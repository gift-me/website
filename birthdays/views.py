from django.contrib import messages
from decimal import Decimal, InvalidOperation
import re
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles.storage import staticfiles_storage
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .auth_views import profile_setup
from .models import (
    CatalogGift,
    SiteSettings,
    UserProfile,
    WishlistItem,
    WithdrawalRequest,
)


def home(request):
    return render(request, "birthdays/home.html", {"now": timezone.now().date()})


def about(request):
    return render(request, "birthdays/about.html")


def contact_redirect(request):
    return redirect(f"{reverse('home')}#contact")


def privacy(request):
    return render(request, "birthdays/privacy.html")


def terms(request):
    return render(request, "birthdays/terms.html")


def accessibility(request):
    return render(request, "birthdays/accessibility.html")


from .fees import calculate_mpesa_withdrawal_fee
from .leaderboard import get_top_gifters

MIN_WITHDRAWAL = Decimal("500")
MPESA_PATTERN = re.compile(r"^07\d{8}$")


def _display_site_url(request):
    settings_obj = SiteSettings.load()
    raw = (settings_obj.website_url or "").strip()
    if raw:
        return raw.replace("https://", "").replace("http://", "").strip("/")
    absolute = request.build_absolute_uri("/")
    return absolute.replace("https://", "").replace("http://", "").strip("/")


def _poster_logo_url(request):
    settings_obj = SiteSettings.load()
    if settings_obj.logo:
        return request.build_absolute_uri(settings_obj.logo.url)
    return request.build_absolute_uri(staticfiles_storage.url("images/logo.svg"))


@login_required
def dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if not profile.gift_slug or not profile.wishlist_slug:
        profile.save()

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add_wishlist":
            titles = request.POST.getlist("wish_title")
            targets = request.POST.getlist("wish_target")
            added = 0
            base_order = profile.wishlist_items.count()
            for idx, (title, target_raw) in enumerate(zip(titles, targets)):
                title = title.strip()
                target_raw = target_raw.strip()
                if not title or not target_raw:
                    continue
                try:
                    target = Decimal(target_raw)
                    if target <= 0:
                        continue
                except (InvalidOperation, TypeError):
                    continue
                WishlistItem.objects.create(
                    profile=profile,
                    title=title,
                    target_amount=target,
                    display_order=base_order + added,
                )
                added += 1
            if added:
                messages.success(request, f"Added {added} wishlist item{'s' if added != 1 else ''}.")
            else:
                messages.error(request, "Enter at least one item with a valid target amount.")
            return redirect("dashboard")

        if action == "delete_wishlist":
            item_id = request.POST.get("item_id")
            profile.wishlist_items.filter(pk=item_id).delete()
            messages.success(request, "Wishlist item removed.")
            return redirect("dashboard")

        if action == "withdraw":
            amount_raw = request.POST.get("amount", "").strip()
            payout_phone = request.POST.get("payout_phone", "").strip()
            try:
                amount = Decimal(amount_raw)
                if amount <= 0:
                    raise InvalidOperation
            except (InvalidOperation, TypeError):
                messages.error(request, "Enter a valid withdrawal amount.")
                return redirect("dashboard")

            if amount < MIN_WITHDRAWAL:
                messages.error(request, "Minimum withdrawal is KES 500.")
                return redirect("dashboard")

            if amount > profile.available_balance:
                messages.error(request, "Withdrawal amount exceeds available balance.")
                return redirect("dashboard")

            if not payout_phone:
                messages.error(request, "M-Pesa number is required.")
                return redirect("dashboard")

            if not MPESA_PATTERN.match(payout_phone):
                messages.error(request, "Enter a valid M-Pesa number.")
                return redirect("dashboard")

            withdrawal_fee = calculate_mpesa_withdrawal_fee(amount)
            if amount + withdrawal_fee > profile.available_balance:
                messages.error(
                    request,
                    f"Insufficient balance. M-Pesa fee of KES {withdrawal_fee} applies to this withdrawal.",
                )
                return redirect("dashboard")

            profile.payout_phone = payout_phone
            profile.save(update_fields=["payout_phone"])

            WithdrawalRequest.objects.create(
                profile=profile,
                amount=amount,
                payout_phone=payout_phone,
                mpesa_withdrawal_fee=withdrawal_fee,
            )
            messages.success(request, "Withdrawal request submitted.")
            return redirect("dashboard")

    display_name = profile.username or request.user.email
    gift_url = request.build_absolute_uri(profile.get_gift_url_path())
    wishlist_url = request.build_absolute_uri(profile.get_wishlist_url_path())
    gifts_qs = profile.gifts_received.all()
    supporters = gifts_qs[:20]
    withdrawals = profile.withdrawals.all()[:20]
    wishlist_items = profile.wishlist_items.all()
    supporters_count = gifts_qs.values("sender_name", "is_anonymous").distinct().count()
    today = timezone.now().date()
    is_birthday_today = bool(
        profile.birthday_date
        and profile.birthday_date.month == today.month
        and profile.birthday_date.day == today.day
    )

    return render(
        request,
        "birthdays/dashboard.html",
        {
            "profile": profile,
            "display_name": display_name,
            "gift_url": gift_url,
            "wishlist_url": wishlist_url,
            "supporters": supporters,
            "withdrawals": withdrawals,
            "wishlist_items": wishlist_items,
            "total_revenue": profile.total_raised,
            "available_balance": profile.available_balance,
            "total_withdrawn": profile.total_withdrawn,
            "gifts_count": profile.gifts_count,
            "supporters_count": supporters_count,
            "profile_incomplete": not profile.setup_completed,
            "is_birthday_today": is_birthday_today,
            "poster_logo_url": _poster_logo_url(request),
            "site_display_url": _display_site_url(request),
        },
    )


def _profile_display_username(profile):
    return profile.username or profile.display_name or profile.user.email.split("@")[0]


def user_gift_page(request, slug):
    profile = get_object_or_404(UserProfile, gift_slug=slug)
    display_username = _profile_display_username(profile)
    display_name = profile.display_name or display_username
    gifts = CatalogGift.objects.filter(is_active=True)
    top_gifters = get_top_gifters(profile, limit=10)
    today = timezone.now().date()
    is_birthday_today = bool(
        profile.birthday_date
        and profile.birthday_date.month == today.month
        and profile.birthday_date.day == today.day
    )

    return render(
        request,
        "birthdays/user_gift.html",
        {
            "profile": profile,
            "display_username": display_username,
            "display_name": display_name,
            "gifts": gifts,
            "top_gifters": top_gifters,
            "is_birthday_today": is_birthday_today,
            "page_type": "gift",
            "page_slug": profile.gift_slug,
        },
    )


def user_wishlist_page(request, slug):
    profile = get_object_or_404(UserProfile, wishlist_slug=slug)
    display_username = _profile_display_username(profile)
    display_name = profile.display_name or display_username
    items = profile.wishlist_items.all()
    top_gifters = get_top_gifters(profile, limit=10)
    today = timezone.now().date()
    is_birthday_today = bool(
        profile.birthday_date
        and profile.birthday_date.month == today.month
        and profile.birthday_date.day == today.day
    )

    return render(
        request,
        "birthdays/user_wishlist.html",
        {
            "profile": profile,
            "display_username": display_username,
            "display_name": display_name,
            "items": items,
            "top_gifters": top_gifters,
            "is_birthday_today": is_birthday_today,
            "page_type": "wishlist",
            "page_slug": profile.wishlist_slug,
        },
    )


def create_birthday_page(request):
    """Legacy URL: celebration pages are created via signup and the dashboard."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("account_signup")
