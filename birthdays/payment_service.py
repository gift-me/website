import secrets
import re
from decimal import Decimal, InvalidOperation

from django.conf import settings as django_settings
from django.db import transaction

from .exceptions import MpesaError
from .fees import (
    calculate_mpesa_deposit_fee,
    calculate_net_to_user,
    calculate_platform_fee,
)
from .models import CatalogGift, MpesaPayment, PaymentAttempt, UserGiftReceived, UserProfile, WishlistItem
from .mpesa import get_mpesa_client, normalize_phone
from .payment_expiry import expire_stale_pending_payments
from .payment_idempotency import remember_idempotent_payment, resolve_idempotent_payment
from .payment_limits import check_stk_rate_limits

MPESA_PATTERN = re.compile(r"^(?:0[17]\d{8}|254[17]\d{8})$")
MESSAGE_MAX_LENGTH = 220


def _fee_settings():
    rate = django_settings.PLATFORM_FEE_PERCENT / Decimal("100")
    cap = django_settings.PLATFORM_FEE_CAP
    return rate, cap


def _profile_display_username(profile):
    return profile.username or profile.display_name or profile.user.email.split("@")[0]


def _unique_account_reference():
    for _ in range(8):
        ref = secrets.token_hex(6).upper()[:12]
        if not MpesaPayment.objects.filter(account_reference=ref).exists():
            return ref
    raise MpesaError("Could not generate payment reference.")


def _resolve_contribution(profile, gift_id, wishlist_item_id, amount_raw):
    catalog_gift = None
    wishlist_item = None
    gift_label = "Gift"

    if wishlist_item_id:
        wishlist_item = profile.wishlist_items.get(pk=wishlist_item_id)
        gift_label = wishlist_item.title
        amount = Decimal(amount_raw)
        if amount <= 0:
            raise InvalidOperation
    elif gift_id:
        catalog_gift = CatalogGift.objects.filter(is_active=True).get(pk=gift_id)
        amount = catalog_gift.amount
        gift_label = catalog_gift.name
    else:
        amount = Decimal(amount_raw)
        if amount <= 0:
            raise InvalidOperation
        gift_label = "Custom gift"

    return catalog_gift, wishlist_item, gift_label, amount


def _apply_fee_fields(payment: MpesaPayment):
    rate, cap = _fee_settings()
    payment.platform_fee = calculate_platform_fee(payment.amount, rate=rate, cap=cap)
    payment.net_amount = calculate_net_to_user(payment.amount, payment.platform_fee)
    payment.mpesa_deposit_fee = calculate_mpesa_deposit_fee(payment.amount)


@transaction.atomic
def create_gift_from_payment(payment: MpesaPayment):
    payment = MpesaPayment.objects.select_for_update().get(pk=payment.pk)
    existing = UserGiftReceived.objects.filter(payment=payment).first()
    if existing:
        return existing

    gift = UserGiftReceived.objects.create(
        profile=payment.profile,
        catalog_gift=payment.catalog_gift,
        wishlist_item=payment.wishlist_item,
        payment=payment,
        sender_name=payment.sender_name,
        payer_phone=payment.payer_phone,
        gift_label=payment.gift_label,
        message=payment.message,
        amount=payment.amount,
        net_amount=payment.net_amount,
        platform_fee=payment.platform_fee,
        is_anonymous=not bool(payment.sender_name.strip()),
    )
    return gift


@transaction.atomic
def mark_payment_completed(payment: MpesaPayment, mpesa_receipt="", result_desc=""):
    payment = MpesaPayment.objects.select_for_update().filter(pk=payment.pk).first()
    if not payment:
        return None
    if payment.status == MpesaPayment.Status.COMPLETED:
        return payment

    if mpesa_receipt:
        duplicate = (
            MpesaPayment.objects.filter(mpesa_receipt=mpesa_receipt, status=MpesaPayment.Status.COMPLETED)
            .exclude(pk=payment.pk)
            .exists()
        )
        if duplicate:
            return payment

    _apply_fee_fields(payment)
    payment.status = MpesaPayment.Status.COMPLETED
    payment.mpesa_receipt = mpesa_receipt or payment.mpesa_receipt
    payment.result_desc = result_desc or payment.result_desc
    payment.save(
        update_fields=[
            "status",
            "mpesa_receipt",
            "result_desc",
            "platform_fee",
            "net_amount",
            "mpesa_deposit_fee",
            "updated_at",
        ]
    )
    create_gift_from_payment(payment)
    return payment


@transaction.atomic
def mark_payment_failed(payment: MpesaPayment, result_desc=""):
    payment = MpesaPayment.objects.select_for_update().filter(pk=payment.pk).first()
    if not payment or payment.status == MpesaPayment.Status.COMPLETED:
        return payment
    payment.status = MpesaPayment.Status.FAILED
    payment.result_desc = result_desc[:255]
    payment.save(update_fields=["status", "result_desc", "updated_at"])
    return payment


def initiate_mpesa_payment(
    profile,
    gift_id,
    wishlist_item_id,
    amount_raw,
    sender_name,
    payer_phone,
    message,
    idempotency_key="",
    client_ip="",
):
    if not MPESA_PATTERN.match(payer_phone.strip()):
        raise MpesaError("Enter a valid M-Pesa number.")

    expire_stale_pending_payments(profile.pk)

    existing = resolve_idempotent_payment(idempotency_key)
    if existing:
        return existing, True

    phone_normalized = normalize_phone(payer_phone)
    check_stk_rate_limits(client_ip, payer_phone.strip(), profile.pk)

    try:
        catalog_gift, wishlist_item, gift_label, amount = _resolve_contribution(
            profile, gift_id, wishlist_item_id, amount_raw
        )
    except (CatalogGift.DoesNotExist, WishlistItem.DoesNotExist, InvalidOperation, TypeError) as exc:
        raise MpesaError("Enter a valid amount and try again.") from exc

    rate, cap = _fee_settings()
    platform_fee = calculate_platform_fee(amount, rate=rate, cap=cap)
    net_amount = calculate_net_to_user(amount, platform_fee)

    payment = MpesaPayment.objects.create(
        profile=profile,
        catalog_gift=catalog_gift,
        wishlist_item=wishlist_item,
        sender_name=sender_name.strip(),
        payer_phone=payer_phone.strip(),
        message=message.strip()[:MESSAGE_MAX_LENGTH],
        amount=amount,
        platform_fee=platform_fee,
        net_amount=net_amount,
        mpesa_deposit_fee=calculate_mpesa_deposit_fee(amount),
        gift_label=gift_label,
        status=MpesaPayment.Status.PENDING,
        account_reference=_unique_account_reference(),
        idempotency_key=(idempotency_key or "").strip(),
    )

    if idempotency_key:
        PaymentAttempt.objects.create(idempotency_key=idempotency_key.strip(), payment=payment)
        remember_idempotent_payment(idempotency_key, payment.pk)

    client = get_mpesa_client()
    desc = gift_label[:13] or "GiftMe"

    try:
        stk = client.stk_push(phone_normalized, amount, payment.account_reference, desc)
    except MpesaError:
        payment.status = MpesaPayment.Status.FAILED
        payment.result_desc = "STK Push failed to start."
        payment.save(update_fields=["status", "result_desc", "updated_at"])
        raise

    payment.checkout_request_id = stk.get("CheckoutRequestID", "")
    payment.merchant_request_id = stk.get("MerchantRequestID", "")
    payment.save(update_fields=["checkout_request_id", "merchant_request_id", "updated_at"])

    return payment, False


def build_whatsapp_share(payment: MpesaPayment, request):
    username = _profile_display_username(payment.profile)
    amount = int(payment.amount)

    if payment.wishlist_item_id:
        page_path = payment.profile.get_wishlist_url_path()
        text = (
            f"I just contributed KES {amount} to @{username}'s wishlist "
            f"({payment.gift_label}) on GiftMe!"
        )
    else:
        page_path = payment.profile.get_gift_url_path()
        text = f"I just sent @{username} a {payment.gift_label} (KES {amount}) on GiftMe!"

    page_url = request.build_absolute_uri(page_path)
    from urllib.parse import quote

    return {
        "message": text,
        "url": f"https://wa.me/?text={quote(f'{text} {page_url}')}",
        "page_url": page_url,
    }


def payment_status_payload(payment: MpesaPayment, request):
    share = None
    if payment.status == MpesaPayment.Status.COMPLETED:
        share = build_whatsapp_share(payment, request)

    return {
        "payment_id": str(payment.pk),
        "status": payment.status,
        "result_desc": payment.result_desc,
        "mpesa_receipt": payment.mpesa_receipt,
        "share": share,
    }
