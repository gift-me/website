import logging
import secrets
import uuid
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .exceptions import MpesaError
from .fees import calculate_mpesa_payout_fee
from .models import Payout, PayoutAuthorization, UserProfile
from .mpesa import get_mpesa_client, normalize_phone

logger = logging.getLogger(__name__)

MIN_PAYOUT = Decimal(str(getattr(settings, "PAYOUT_MIN_AMOUNT", 500)))


def _otp_expiry():
    minutes = getattr(settings, "PAYOUT_OTP_EXPIRY_MINUTES", 10)
    return timezone.now() + timezone.timedelta(minutes=minutes)


def _generate_otp_code():
    return f"{secrets.randbelow(1_000_000):06d}"


def _validate_amount(amount_raw):
    try:
        amount = Decimal(f"{amount_raw}")
    except (InvalidOperation, TypeError) as exc:
        raise MpesaError("Enter a valid payout amount.") from exc

    if amount <= 0 or amount != amount.to_integral_value():
        raise MpesaError("Payout amount must be a whole number of KES.")

    if amount < MIN_PAYOUT:
        raise MpesaError(f"Minimum payout is KES {int(MIN_PAYOUT)}.")

    return amount


def _validate_payout_phone(phone_raw):
    phone_raw = (phone_raw or "").strip()
    if not phone_raw:
        raise MpesaError("M-Pesa number is required.")
    return normalize_phone(phone_raw)


def _send_otp_email(user, code, amount):
    subject = "Your GiftMe payout verification code"
    expiry = getattr(settings, "PAYOUT_OTP_EXPIRY_MINUTES", 10)
    text_message = (
        f"Hi,\n\n"
        f"Your verification code for a KES {int(amount)} payout is: {code}\n\n"
        f"This code expires in {expiry} minutes.\n"
        f"If you did not request this payout, ignore this email.\n\n"
        f"— GiftMe"
    )
    html_message = f"""
    <div style="font-family:Inter,Segoe UI,sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#222;">
      <p style="margin:0 0 8px;font-weight:700;color:#E63946;">GiftMe</p>
      <h2 style="margin:0 0 12px;font-size:20px;">Payout verification</h2>
      <p style="margin:0 0 16px;color:#555;line-height:1.5;">
        Use this code to confirm your KES {int(amount)} payout. It expires in {expiry} minutes.
      </p>
      <p style="margin:0 0 20px;font-size:28px;letter-spacing:0.28em;font-weight:700;color:#222;">{code}</p>
      <p style="margin:0;color:#888;font-size:13px;line-height:1.45;">
        If you did not request this payout, you can ignore this email.
      </p>
    </div>
    """
    send_mail(
        subject,
        text_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
        html_message=html_message,
    )


@transaction.atomic
def initiate_payout_authorization(profile: UserProfile, amount_raw, payout_phone_raw):
    profile = UserProfile.objects.select_for_update().get(pk=profile.pk)
    amount = _validate_amount(amount_raw)
    payout_phone = _validate_payout_phone(payout_phone_raw)

    if amount > profile.available_balance:
        raise MpesaError("Payout amount exceeds available balance.")

    profile.payout_phone = payout_phone
    profile.save(update_fields=["payout_phone"])

    code = _generate_otp_code()
    authorization = PayoutAuthorization.objects.create(
        profile=profile,
        amount=amount,
        payout_phone=payout_phone,
        code_hash=make_password(code),
        expires_at=_otp_expiry(),
    )

    try:
        _send_otp_email(profile.user, code, amount)
    except Exception as exc:
        authorization.delete()
        logger.exception("Failed to send payout OTP email")
        raise MpesaError("Could not send verification email. Check email settings and try again.") from exc

    return authorization


def verify_and_disburse(profile: UserProfile, authorization_id, code_raw):
    """
    Verify OTP, soft-hold with a PROCESSING payout, then submit B2C.

    The M-Pesa HTTP call runs outside the DB transaction so a failure can
    commit FAILED and release the hold. Balance is only permanently deducted
    when mark_payout_completed runs after a successful B2C callback.
    """
    with transaction.atomic():
        profile = UserProfile.objects.select_for_update().get(pk=profile.pk)
        code = (code_raw or "").strip()
        if not code:
            raise MpesaError("Enter the verification code from your email.")

        authorization = (
            PayoutAuthorization.objects.select_for_update()
            .filter(pk=authorization_id, profile=profile, verified_at__isnull=True)
            .first()
        )
        if not authorization:
            raise MpesaError("Verification session not found. Start the payout again.")

        if authorization.expires_at <= timezone.now():
            raise MpesaError("Verification code expired. Start the payout again.")

        if not check_password(code, authorization.code_hash):
            raise MpesaError("Invalid verification code.")

        free_balance = profile.total_raised - profile.total_paid_out - profile.in_flight_payout_total
        if authorization.amount > free_balance:
            raise MpesaError("Payout amount exceeds available balance.")

        payout_fee = calculate_mpesa_payout_fee(authorization.amount)
        if authorization.amount + payout_fee > free_balance:
            raise MpesaError(
                f"Insufficient balance. M-Pesa fee of KES {int(payout_fee)} applies to this payout."
            )

        authorization.verified_at = timezone.now()
        authorization.save(update_fields=["verified_at"])

        originator_id = str(uuid.uuid4())
        # Soft hold only — available_balance drops via in_flight_payout_total until
        # APPROVED (permanent) or FAILED (released).
        payout = Payout.objects.create(
            kind=Payout.Kind.USER,
            profile=profile,
            amount=authorization.amount,
            payout_phone=authorization.payout_phone,
            payout_fee=payout_fee,
            status=Payout.Status.PROCESSING,
            originator_conversation_id=originator_id,
        )
        authorization.payout = payout
        authorization.save(update_fields=["payout"])
        payout_id = payout.pk
        payout_phone = authorization.payout_phone
        payout_amount = authorization.amount

    # B2C is outside the atomic block so FAILED can commit if Daraja rejects us.
    try:
        response = get_mpesa_client().b2c_payment(
            phone=payout_phone,
            amount=payout_amount,
            remarks="GiftMe payout",
            occasion=f"payout:{payout_id}",
            originator_conversation_id=originator_id,
        )
    except Exception as exc:
        payout = Payout.objects.filter(pk=payout_id).first()
        if payout:
            mark_payout_failed(
                payout,
                str(exc) if isinstance(exc, MpesaError) else "Payout could not be submitted to M-Pesa.",
            )
        logger.exception("B2C payout request failed for payout %s", payout_id)
        if isinstance(exc, MpesaError):
            raise
        raise MpesaError("Payout could not be submitted to M-Pesa. Your balance has been restored.") from exc

    payout = Payout.objects.get(pk=payout_id)
    payout.originator_conversation_id = response.get("OriginatorConversationID", "")
    payout.conversation_id = response.get("ConversationID", "")
    payout.result_desc = response.get("ResponseDescription", "B2C request accepted.")
    payout.save(update_fields=["originator_conversation_id", "conversation_id", "result_desc"])

    return payout


def mark_payout_completed(payout: Payout, transaction_id="", result_desc=""):
    """Permanently deduct user balance by marking the payout APPROVED."""
    if payout.status == Payout.Status.APPROVED:
        return payout

    payout.status = Payout.Status.APPROVED
    payout.mpesa_transaction_id = transaction_id or payout.mpesa_transaction_id
    payout.result_desc = result_desc or payout.result_desc or "Payout completed."
    payout.processed_at = timezone.now()
    payout.save(update_fields=["status", "mpesa_transaction_id", "result_desc", "processed_at"])
    return payout


def mark_payout_failed(payout: Payout, result_desc=""):
    """Release the soft hold — funds return to available_balance."""
    if payout.status in (Payout.Status.APPROVED, Payout.Status.FAILED):
        return payout

    payout.status = Payout.Status.FAILED
    payout.result_desc = result_desc or payout.result_desc or "Payout failed."
    payout.processed_at = timezone.now()
    payout.save(update_fields=["status", "result_desc", "processed_at"])
    return payout


# Backwards-compatible aliases

def payout_status_payload(payout: Payout):
    return {
        "payout_id": str(payout.pk),
        "status": payout.status,
        "amount": str(payout.amount),
        "result_desc": payout.result_desc,
        "mpesa_transaction_id": payout.mpesa_transaction_id,
    }


def find_payout_for_b2c_callback(parsed):
    """Match a B2C result/timeout payload to a payout row."""
    originator_id = parsed.get("originator_conversation_id")
    conversation_id = parsed.get("conversation_id")
    transaction_id = parsed.get("transaction_id")
    occasion = f"{parsed.get('occasion') or ''}"

    payout = None
    if originator_id:
        payout = Payout.objects.filter(originator_conversation_id=originator_id).first()
    if not payout and conversation_id:
        payout = Payout.objects.filter(conversation_id=conversation_id).first()
    if not payout and transaction_id:
        payout = Payout.objects.filter(mpesa_transaction_id=transaction_id).first()
    if not payout and occasion.startswith("payout:"):
        try:
            payout = Payout.objects.filter(pk=int(occasion.split(":", 1)[1])).first()
        except (TypeError, ValueError):
            payout = None
    return payout
