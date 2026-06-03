from django.contrib import messages
from decimal import Decimal, InvalidOperation
import re
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .auth_views import profile_setup
from .models import BirthdayPage, CatalogGift, GiftContribution, GiftOption, UserGiftReceived, UserProfile, WishlistItem, WithdrawalRequest


DEFAULT_GIFT_OPTIONS = [
    ("Birthday Cake", "fa-cake-candles", 100, "cake"),
    ("Balloons", "fa-balloon", 50, "balloons"),
    ("Pizza", "fa-pizza-slice", 300, "pizza"),
    ("Burger", "fa-burger", 250, "burger"),
    ("Coffee", "fa-mug-hot", 100, "coffee"),
    ("Champagne", "fa-champagne-glasses", 500, "sparkles"),
    ("Vacation Fund", "fa-plane-departure", 1000, "stars"),
    ("Car Fuel", "fa-gas-pump", 500, "fuel"),
    ("Surprise Gift", "fa-gift", None, "confetti"),
]


def home(request):
    pages = BirthdayPage.objects.all()[:6]
    return render(request, "birthdays/home.html", {"pages": pages, "now": timezone.now().date()})


def about(request):
    return render(request, "birthdays/about.html")


def contact(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        request_type = request.POST.get("request_type", "").strip()
        details = request.POST.get("details", "").strip()
        if name and email and request_type and details:
            messages.success(
                request,
                "Thank you. We have received your request and will reach out shortly.",
            )
            return redirect("contact")
        messages.error(request, "Please fill in all required contact fields.")
    return render(request, "birthdays/contact.html")


def privacy(request):
    return render(request, "birthdays/privacy.html")


def terms(request):
    return render(request, "birthdays/terms.html")


MIN_WITHDRAWAL = Decimal("500")
MPESA_PATTERN = re.compile(r"^07\d{8}$")


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

            profile.payout_phone = payout_phone
            profile.save(update_fields=["payout_phone"])

            WithdrawalRequest.objects.create(
                profile=profile, amount=amount, payout_phone=payout_phone
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
        },
    )


def _profile_display_username(profile):
    return profile.username or profile.display_name or profile.user.email.split("@")[0]


def user_gift_page(request, slug):
    profile = get_object_or_404(UserProfile, gift_slug=slug)
    display_username = _profile_display_username(profile)
    gifts = CatalogGift.objects.filter(is_active=True)

    return render(
        request,
        "birthdays/user_gift.html",
        {
            "profile": profile,
            "display_username": display_username,
            "gifts": gifts,
            "page_type": "gift",
            "page_slug": profile.gift_slug,
        },
    )


def user_wishlist_page(request, slug):
    profile = get_object_or_404(UserProfile, wishlist_slug=slug)
    display_username = _profile_display_username(profile)
    items = profile.wishlist_items.all()

    return render(
        request,
        "birthdays/user_wishlist.html",
        {
            "profile": profile,
            "display_username": display_username,
            "items": items,
            "page_type": "wishlist",
            "page_slug": profile.wishlist_slug,
        },
    )


@transaction.atomic
def create_birthday_page(request):
    if request.method == "POST":
        form = BirthdayPageForm(request.POST)
        if form.is_valid():
            page = form.save(commit=False)
            page.owner = request.user if request.user.is_authenticated else None
            page.save()
            for idx, option in enumerate(DEFAULT_GIFT_OPTIONS):
                label, icon, amount, animation = option
                GiftOption.objects.create(
                    page=page, label=label, icon=icon, amount=amount, animation=animation, display_order=idx
                )
            messages.success(request, "Birthday page created. Share your link and start receiving gifts.")
            return redirect(page.get_absolute_url())
    else:
        form = BirthdayPageForm()
    return render(request, "birthdays/create_page.html", {"form": form})


@transaction.atomic
def birthday_detail(request, slug):
    page = get_object_or_404(BirthdayPage, slug=slug)

    if request.method == "POST":
        gift_form = GiftContributionForm(request.POST, page=page)
        if gift_form.is_valid():
            gift = gift_form.save(commit=False)
            gift.page = page
            gift.save()
            messages.success(
                request,
                "Gift added successfully. Payment integration is still pending, but this records the intention.",
            )
            return redirect(page.get_absolute_url())
    else:
        gift_form = GiftContributionForm(page=page, initial={"amount": 100})

    gifts = page.gifts.select_related("option")[:12]
    return render(
        request,
        "birthdays/birthday_detail.html",
        {"page": page, "gift_form": gift_form, "gifts": gifts, "recent_count": page.gifts_count},
    )


def seed_demo(request):
    if BirthdayPage.objects.filter(slug="julius28").exists():
        page = BirthdayPage.objects.get(slug="julius28")
        return redirect(page.get_absolute_url())

    with transaction.atomic():
        page = BirthdayPage.objects.create(
            name="Julius",
            slug="julius28",
            age_turning=28,
            birthday_date=timezone.now().date(),
            bio="Celebrating 28 years. Help me unlock birthday treats and memories.",
            goal_amount=80000,
            payout_phone="+254700000000",
            payout_wallet_name="M-Pesa",
        )
        for idx, option in enumerate(DEFAULT_GIFT_OPTIONS):
            label, icon, amount, animation = option
            GiftOption.objects.create(
                page=page, label=label, icon=icon, amount=amount, animation=animation, display_order=idx
            )

        pizza = page.gift_options.get(label="Pizza")
        cake = page.gift_options.get(label="Birthday Cake")
        GiftContribution.objects.create(page=page, option=cake, sender_name="Brian", amount=100, message="Enjoy!")
        GiftContribution.objects.create(page=page, option=pizza, sender_name="Mary", amount=300, message="Happy day!")
        GiftContribution.objects.create(page=page, option=pizza, sender_name="", is_anonymous=True, amount=500)

    return redirect(page.get_absolute_url())
