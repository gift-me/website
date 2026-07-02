import logging
import secrets
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .exceptions import MpesaError
from .fees import calculate_mpesa_withdrawal_fee
from .models import UserProfile, WithdrawalAuthorization, WithdrawalRequest
from .mpesa import get_mpesa_client, normalize_phone

logger = logging.getLogger(__name__)

MIN_WITHDRAWAL = Decimal("500")


def _otp_expiry():
    minutes = getattr(settings, "WITHDRAWAL_OTP_EXPIRY_MINUTES", 10)
    return timezone.now() + timezone.timedelta(minutes=minutes)


def _generate_otp_code():
    return f"{secrets.randbelow(1_000_000):06d}"


def _validate_amount(amount_raw):
    try:
        amount = Decimal(f"{amount_raw}")
    except (InvalidOperation, TypeError) as exc:
        raise MpesaError("Enter a valid withdrawal amount.") from exc

    if amount <= 0 or amount != amount.to_integral_value():
        raise MpesaError("Withdrawal amount must be a whole number of KES.")

    if amount < MIN_WITHDRAWAL:
        raise MpesaError(f"Minimum withdrawal is KES {int(MIN_WITHDRAWAL)}.")

    return amount


def _validate_payout_phone(phone_raw):
    phone_raw = (phone_raw or "").strip()
    if not phone_raw:
        raise MpesaError("M-Pesa number is required.")
    return normalize_phone(phone_raw)


def _send_otp_email(user, code, amount):
    subject = "Your GiftMe withdrawal verification code"
    message = (
        f"Hi,\n\n"
        f"Your verification code for a KES {int(amount)} withdrawal is: {code}\n\n"
        f"This code expires in {getattr(settings, 'WITHDRAWAL_OTP_EXPIRY_MINUTES', 10)} minutes.\n"
        f"If you did not request this withdrawal, you can ignore this email.\n\n"
        f"— GiftMe"
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


@transaction.atomic
def initiate_withdrawal_authorization(profile: UserProfile, amount_raw, payout_phone_raw):
    profile = UserProfile.objects.select_for_update().get(pk=profile.pk)
    amount = _validate_amount(amount_raw)
    payout_phone = _validate_payout_phone(payout_phone_raw)

    if amount > profile.available_balance:
        raise MpesaError("Withdrawal amount exceeds available balance.")

    profile.payout_phone = payout_phone
    profile.save(update_fields=["payout_phone"])

    code = _generate_otp_code()
    authorization = WithdrawalAuthorization.objects.create(
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
        logger.exception("Failed to send withdrawal OTP email")
        raise MpesaError("Could not send verification email. Check email settings and try again.") from exc

    return authorization


@transaction.atomic
def verify_and_disburse(profile: UserProfile, authorization_id, code_raw):
    profile = UserProfile.objects.select_for_update().get(pk=profile.pk)
    code = (code_raw or "").strip()
    if not code:
        raise MpesaError("Enter the verification code from your email.")

    authorization = (
        WithdrawalAuthorization.objects.select_for_update()
        .filter(pk=authorization_id, profile=profile, verified_at__isnull=True)
        .first()
    )
    if not authorization:
        raise MpesaError("Verification session not found. Start the withdrawal again.")

    if authorization.expires_at <= timezone.now():
        raise MpesaError("Verification code expired. Start the withdrawal again.")

    if not check_password(code, authorization.code_hash):
        raise MpesaError("Invalid verification code.")

    if authorization.amount > profile.total_raised - profile.reserved_withdrawal_total:
        raise MpesaError("Withdrawal amount exceeds available balance.")

    withdrawal_fee = calculate_mpesa_withdrawal_fee(authorization.amount)
    if authorization.amount + withdrawal_fee > profile.total_raised - profile.reserved_withdrawal_total:
        raise MpesaError(
            f"Insufficient balance. M-Pesa fee of KES {int(withdrawal_fee)} applies to this withdrawal."
        )

    authorization.verified_at = timezone.now()
    authorization.save(update_fields=["verified_at"])

    withdrawal = WithdrawalRequest.objects.create(
        profile=profile,
        amount=authorization.amount,
        payout_phone=authorization.payout_phone,
        mpesa_withdrawal_fee=withdrawal_fee,
        status=WithdrawalRequest.Status.PROCESSING,
    )
    authorization.withdrawal = withdrawal
    authorization.save(update_fields=["withdrawal"])

    client = get_mpesa_client()
    try:
        response = client.b2c_payment(
            phone=authorization.payout_phone,
            amount=authorization.amount,
            remarks="GiftMe withdrawal",
        )
    except MpesaError as exc:
        withdrawal.status = WithdrawalRequest.Status.FAILED
        withdrawal.result_desc = str(exc)
        withdrawal.processed_at = timezone.now()
        withdrawal.save(update_fields=["status", "result_desc", "processed_at"])
        raise

    withdrawal.originator_conversation_id = response.get("OriginatorConversationID", "")
    withdrawal.conversation_id = response.get("ConversationID", "")
    withdrawal.result_desc = response.get("ResponseDescription", "B2C request accepted.")
    withdrawal.save(
        update_fields=["originator_conversation_id", "conversation_id", "result_desc"]
    )

    return withdrawal


def mark_withdrawal_completed(withdrawal: WithdrawalRequest, transaction_id="", result_desc=""):
    if withdrawal.status == WithdrawalRequest.Status.APPROVED:
        return withdrawal

    withdrawal.status = WithdrawalRequest.Status.APPROVED
    withdrawal.mpesa_transaction_id = transaction_id or withdrawal.mpesa_transaction_id
    withdrawal.result_desc = result_desc or withdrawal.result_desc or "Withdrawal completed."
    withdrawal.processed_at = timezone.now()
    withdrawal.save(
        update_fields=["status", "mpesa_transaction_id", "result_desc", "processed_at"]
    )
    return withdrawal


def mark_withdrawal_failed(withdrawal: WithdrawalRequest, result_desc=""):
    if withdrawal.status in (WithdrawalRequest.Status.APPROVED, WithdrawalRequest.Status.FAILED):
        return withdrawal

    withdrawal.status = WithdrawalRequest.Status.FAILED
    withdrawal.result_desc = result_desc or withdrawal.result_desc or "Withdrawal failed."
    withdrawal.processed_at = timezone.now()
    withdrawal.save(update_fields=["status", "result_desc", "processed_at"])
    return withdrawal


def withdrawal_status_payload(withdrawal: WithdrawalRequest):
    return {
        "withdrawal_id": str(withdrawal.pk),
        "status": withdrawal.status,
        "amount": str(withdrawal.amount),
        "result_desc": withdrawal.result_desc,
        "mpesa_transaction_id": withdrawal.mpesa_transaction_id,
    }
