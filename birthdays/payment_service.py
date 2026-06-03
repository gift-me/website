import secrets
import re
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.urls import reverse

from .exceptions import MpesaError
from .models import CatalogGift, MpesaPayment, UserGiftReceived, UserProfile, WishlistItem
from .mpesa import get_mpesa_client, normalize_phone

MPESA_PATTERN = re.compile(r"^07\d{8}$")
MESSAGE_MAX_LENGTH = 220


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


@transaction.atomic
def create_gift_from_payment(payment: MpesaPayment):
    if payment.gift_record_id:
        return payment.gift_record

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
        is_anonymous=not bool(payment.sender_name.strip()),
    )
    return gift


@transaction.atomic
def mark_payment_completed(payment: MpesaPayment, mpesa_receipt="", result_desc=""):
    if payment.status == MpesaPayment.Status.COMPLETED:
        return payment

    payment.status = MpesaPayment.Status.COMPLETED
    payment.mpesa_receipt = mpesa_receipt or payment.mpesa_receipt
    payment.result_desc = result_desc or payment.result_desc
    payment.save(update_fields=["status", "mpesa_receipt", "result_desc", "updated_at"])
    create_gift_from_payment(payment)
    return payment


@transaction.atomic
def mark_payment_failed(payment: MpesaPayment, result_desc=""):
    if payment.status == MpesaPayment.Status.COMPLETED:
        return payment
    payment.status = MpesaPayment.Status.FAILED
    payment.result_desc = result_desc[:255]
    payment.save(update_fields=["status", "result_desc", "updated_at"])
    return payment


def initiate_mpesa_payment(profile, gift_id, wishlist_item_id, amount_raw, sender_name, payer_phone, message):
    if not MPESA_PATTERN.match(payer_phone.strip()):
        raise MpesaError("Enter a valid M-Pesa number.")

    try:
        catalog_gift, wishlist_item, gift_label, amount = _resolve_contribution(
            profile, gift_id, wishlist_item_id, amount_raw
        )
    except (CatalogGift.DoesNotExist, WishlistItem.DoesNotExist, InvalidOperation, TypeError) as exc:
        raise MpesaError("Enter a valid amount and try again.") from exc

    payment = MpesaPayment.objects.create(
        profile=profile,
        catalog_gift=catalog_gift,
        wishlist_item=wishlist_item,
        sender_name=sender_name.strip(),
        payer_phone=payer_phone.strip(),
        message=message.strip()[:MESSAGE_MAX_LENGTH],
        amount=amount,
        gift_label=gift_label,
        status=MpesaPayment.Status.PENDING,
        account_reference=_unique_account_reference(),
    )

    client = get_mpesa_client()
    phone = normalize_phone(payer_phone)
    desc = gift_label[:13] or "GiftMe"

    try:
        stk = client.stk_push(phone, amount, payment.account_reference, desc)
    except MpesaError:
        payment.status = MpesaPayment.Status.FAILED
        payment.result_desc = "STK Push failed to start."
        payment.save(update_fields=["status", "result_desc", "updated_at"])
        raise

    payment.checkout_request_id = stk.get("CheckoutRequestID", "")
    payment.merchant_request_id = stk.get("MerchantRequestID", "")
    payment.save(update_fields=["checkout_request_id", "merchant_request_id", "updated_at"])

    return payment


def build_whatsapp_share(payment: MpesaPayment, request):
    username = _profile_display_username(payment.profile)
    sender = payment.sender_name.strip() or "Someone"
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
