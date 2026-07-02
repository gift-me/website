import re
from decimal import Decimal, InvalidOperation

from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from birthdays.fees import calculate_mpesa_withdrawal_fee
from birthdays.models import CatalogGift, HouseWithdrawal, MpesaPayment, SiteSettings, WithdrawalRequest
from birthdays.safe_cache import cache_get, cache_incr, cache_set

from .decorators import staff_required
from .services import (
    filter_house_withdrawals,
    filter_payments,
    filter_user_withdrawals,
    gifts_last_7_days,
    overview_stats,
    payment_status_chart,
    revenue_breakdown_chart,
    revenue_chart,
)

MPESA_PATTERN = re.compile(r"^07\d{8}$")


def _ops_ctx(request, page):
    return {"ops_page": page, "user": request.user}


@require_GET
def ops_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("ops-overview")
    return render(request, "ops/login.html")


@require_POST
def ops_login_submit(request):
    ip = request.META.get("REMOTE_ADDR", "")
    block_key = f"ops_login_fail:{ip}"
    if (cache_get(block_key) or 0) >= 10:
        messages.error(request, "Too many failed attempts. Try again later.")
        return redirect("ops-login")

    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "")
    user = authenticate(request, username=username, password=password)
    if not user or not user.is_staff:
        count = cache_incr(block_key) or 1
        if count == 1:
            cache_set(block_key, 1, timeout=900)
        messages.error(request, "Invalid staff credentials.")
        return redirect("ops-login")

    login(request, user)
    return redirect("ops-overview")


@require_POST
@staff_required
def ops_logout(request):
    logout(request)
    return redirect("ops-login")


@require_GET
@staff_required
def ops_overview(request):
    stats = overview_stats()
    return render(
        request,
        "ops/overview.html",
        {
            **_ops_ctx(request, "overview"),
            "stats": stats,
            "revenue_chart": revenue_chart(),
            "gifts_7d_chart": gifts_last_7_days(),
            "status_chart": payment_status_chart(),
            "breakdown_chart": revenue_breakdown_chart(),
        },
    )


@require_GET
@staff_required
def ops_deposits(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    payments = filter_payments(q, status)[:200]
    return render(
        request,
        "ops/deposits.html",
        {**_ops_ctx(request, "deposits"), "payments": payments, "q": q, "status": status},
    )


@require_GET
@staff_required
def ops_withdrawals(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    withdrawals = filter_user_withdrawals(q, status)[:200]
    return render(
        request,
        "ops/withdrawals.html",
        {**_ops_ctx(request, "withdrawals"), "withdrawals": withdrawals, "q": q, "status": status},
    )


@require_GET
@staff_required
def ops_house_withdrawals(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    rows = filter_house_withdrawals(q, status)[:200]
    return render(
        request,
        "ops/house_withdrawals.html",
        {**_ops_ctx(request, "house"), "rows": rows, "q": q, "status": status},
    )


@require_GET
@staff_required
def ops_settings(request):
    settings_obj = SiteSettings.load()
    return render(
        request,
        "ops/settings.html",
        {
            **_ops_ctx(request, "settings"),
            "settings_obj": settings_obj,
            "platform_fee_percent": django_settings.PLATFORM_FEE_PERCENT,
            "platform_fee_cap": django_settings.PLATFORM_FEE_CAP,
        },
    )


@require_POST
@staff_required
def ops_settings_save(request):
    settings_obj = SiteSettings.load()
    settings_obj.contact_email = request.POST.get("contact_email", "").strip()
    settings_obj.contact_phone = request.POST.get("contact_phone", "").strip()
    settings_obj.facebook_url = request.POST.get("facebook_url", "").strip()
    settings_obj.tiktok_url = request.POST.get("tiktok_url", "").strip()
    settings_obj.instagram_url = request.POST.get("instagram_url", "").strip()
    settings_obj.website_url = request.POST.get("website_url", "").strip().replace("https://", "").replace("http://", "").strip("/")
    if request.FILES.get("logo"):
        settings_obj.logo = request.FILES["logo"]
    if request.FILES.get("favicon"):
        settings_obj.favicon = request.FILES["favicon"]
    settings_obj.save()
    messages.success(request, "Site settings saved.")
    return redirect("ops-settings")


@require_POST
@staff_required
def ops_house_withdraw(request):
    from .services import available_house_profit

    amount_raw = request.POST.get("amount", "").strip()
    phone = request.POST.get("payout_phone", "").strip()
    try:
        amount = Decimal(amount_raw)
        if amount <= 0:
            raise InvalidOperation
    except (InvalidOperation, TypeError):
        return JsonResponse({"success": False, "error": "Enter a valid amount."}, status=400)

    if amount > available_house_profit():
        return JsonResponse({"success": False, "error": "Amount exceeds available house profit."}, status=400)

    if not MPESA_PATTERN.match(phone):
        return JsonResponse({"success": False, "error": "Enter a valid M-Pesa number."}, status=400)

    fee = calculate_mpesa_withdrawal_fee(amount)
    HouseWithdrawal.objects.create(
        amount=amount,
        payout_phone=phone,
        mpesa_withdrawal_fee=fee,
        created_by=request.user,
        status=HouseWithdrawal.Status.PENDING,
    )
    return JsonResponse({"success": True, "message": "House withdrawal request recorded.", "fee": str(fee)})


@require_GET
@staff_required
def ops_gifts(request):
    edit_id = request.GET.get("edit", "").strip()
    edit_gift = None
    if edit_id:
        edit_gift = get_object_or_404(CatalogGift, pk=edit_id)
    gifts = CatalogGift.objects.all().order_by("display_order", "id")
    return render(
        request,
        "ops/gifts.html",
        {**_ops_ctx(request, "gifts"), "gifts": gifts, "edit_gift": edit_gift},
    )


@require_POST
@staff_required
def ops_gifts_save(request):
    gift_id = request.POST.get("gift_id", "").strip()
    name = request.POST.get("name", "").strip()
    description = request.POST.get("description", "").strip()
    amount_raw = request.POST.get("amount", "").strip()
    display_order_raw = request.POST.get("display_order", "0").strip()
    is_active = request.POST.get("is_active") == "on"

    if not name or not amount_raw:
        messages.error(request, "Name and amount are required.")
        return redirect(f"{reverse('ops-gifts')}?edit={gift_id}" if gift_id else "ops-gifts")

    try:
        amount = Decimal(amount_raw)
        if amount <= 0:
            raise InvalidOperation
        display_order = int(display_order_raw)
        if display_order < 0:
            raise ValueError
    except (InvalidOperation, ValueError, TypeError):
        messages.error(request, "Enter a valid amount and sort order.")
        return redirect(f"{reverse('ops-gifts')}?edit={gift_id}" if gift_id else "ops-gifts")

    if gift_id:
        gift = get_object_or_404(CatalogGift, pk=gift_id)
    else:
        if not request.FILES.get("image"):
            messages.error(request, "Image is required for new gifts.")
            return redirect("ops-gifts")
        gift = CatalogGift()

    gift.name = name
    gift.description = description
    gift.amount = amount
    gift.display_order = display_order
    gift.is_active = is_active
    if request.FILES.get("image"):
        gift.image = request.FILES["image"]

    gift.save()
    messages.success(request, f"Gift “{gift.name}” saved.")
    return redirect("ops-gifts")


@require_POST
@staff_required
def ops_gifts_delete(request):
    gift_id = request.POST.get("gift_id", "").strip()
    gift = get_object_or_404(CatalogGift, pk=gift_id)
    name = gift.name
    gift.delete()
    messages.success(request, f"Gift “{name}” deleted.")
    return redirect("ops-gifts")
