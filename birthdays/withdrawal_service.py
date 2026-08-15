import logging
import secrets
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import models, transaction
from django.utils import timezone

from .exceptions import MpesaError
from .models import UserProfile, WithdrawalAuthorization, WithdrawalRequest
from .mpesa import normalize_phone

logger = logging.getLogger(__name__)

def minimum_withdrawal_amount():
    """Return the minimum withdrawal configured by the deployment environment."""
    return Decimal(str(getattr(settings, "WITHDRAWAL_MIN_AMOUNT", "500")))


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

    minimum = minimum_withdrawal_amount()
    if amount < minimum:
        raise MpesaError(f"Minimum withdrawal is KES {int(minimum)}.")

    return amount


def _validate_payout_phone(phone_raw):
    phone_raw = (phone_raw or "").strip()
    if not phone_raw:
        raise MpesaError("M-Pesa number is required.")
    return normalize_phone(phone_raw)


def _send_otp_email(user, code, amount):
    subject = "Your GiftMe withdrawal verification code"
    expiry = getattr(settings, "WITHDRAWAL_OTP_EXPIRY_MINUTES", 10)
    text_message = (
        f"Hi,\n\n"
        f"Your verification code for a KES {int(amount)} withdrawal is: {code}\n\n"
        f"This code expires in {expiry} minutes.\n"
        f"If you did not request this withdrawal, ignore this email.\n\n"
        f"— GiftMe"
    )
    html_message = f"""
    <div style="font-family:Inter,Segoe UI,sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#222;">
      <p style="margin:0 0 8px;font-weight:700;color:#E63946;">GiftMe</p>
      <h2 style="margin:0 0 12px;font-size:20px;">Withdrawal verification</h2>
      <p style="margin:0 0 16px;color:#555;line-height:1.5;">
        Use this code to confirm your KES {int(amount)} withdrawal. It expires in {expiry} minutes.
      </p>
      <p style="margin:0 0 20px;font-size:28px;letter-spacing:0.28em;font-weight:700;color:#222;">{code}</p>
      <p style="margin:0;color:#888;font-size:13px;line-height:1.45;">
        If you did not request this withdrawal, you can ignore this email.
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


def _send_withdrawal_update_email(withdrawal, subject, heading, message, closing=""):
    user = withdrawal.profile.user
    text_message = (
        f"Hi,\n\n{message}\n\n"
        f"Amount: KES {int(withdrawal.amount)}\n"
        f"M-Pesa number: {withdrawal.payout_phone}\n"
        f"{closing}\n\n— GiftMe"
    )
    html_message = f"""
    <div style="font-family:Inter,Segoe UI,sans-serif;max-width:520px;margin:0 auto;padding:24px;color:#222;">
      <p style="margin:0 0 8px;font-weight:700;color:#E63946;">GiftMe</p>
      <h2 style="margin:0 0 12px;font-size:20px;">{heading}</h2>
      <p style="margin:0 0 16px;color:#555;line-height:1.5;">{message}</p>
      <p style="margin:0 0 8px;"><strong>Amount:</strong> KES {int(withdrawal.amount)}</p>
      <p style="margin:0;color:#555;"><strong>M-Pesa number:</strong> {withdrawal.payout_phone}</p>
      <p style="margin:16px 0 0;color:#555;line-height:1.5;">{closing}</p>
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


def _send_withdrawal_update_email_safe(withdrawal, subject, heading, message, closing=""):
    try:
        _send_withdrawal_update_email(withdrawal, subject, heading, message, closing)
    except Exception:
        logger.exception("Failed to send withdrawal update email for withdrawal %s", withdrawal.pk)


def send_withdrawal_processing_email(withdrawal):
    _send_withdrawal_update_email_safe(
        withdrawal,
        "Your GiftMe withdrawal is being processed",
        "Withdrawal request received",
        "Your withdrawal request is being processed. It normally takes up to 24 hours.",
        "We will email you again as soon as the withdrawal has been processed.",
    )


def send_withdrawal_approved_email(withdrawal):
    _send_withdrawal_update_email_safe(
        withdrawal,
        "Your GiftMe withdrawal has been processed",
        "Withdrawal processed",
        "Your withdrawal has been processed and sent to your M-Pesa number.",
    )


def send_withdrawal_rejected_email(withdrawal):
    reason = withdrawal.result_desc or "The request could not be approved at this time."
    _send_withdrawal_update_email_safe(
        withdrawal,
        "Your GiftMe withdrawal request was rejected",
        "Withdrawal request rejected",
        reason,
        "The requested amount has been returned to your available GiftMe balance.",
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
def verify_and_create_withdrawal(profile: UserProfile, authorization_id, code_raw):
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

    other_pending_otp_total = profile.withdrawal_authorizations.filter(
        verified_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).exclude(pk=authorization.pk).aggregate(total=models.Sum("amount"))["total"] or Decimal("0")
    available_for_request = profile.total_raised - profile.reserved_withdrawal_total - other_pending_otp_total
    if authorization.amount > available_for_request:
        raise MpesaError("Withdrawal amount exceeds available balance.")

    authorization.verified_at = timezone.now()
    authorization.save(update_fields=["verified_at"])

    withdrawal = WithdrawalRequest.objects.create(
        profile=profile,
        amount=authorization.amount,
        payout_phone=authorization.payout_phone,
        mpesa_withdrawal_fee=Decimal("0"),
        status=WithdrawalRequest.Status.PENDING,
    )
    authorization.withdrawal = withdrawal
    authorization.save(update_fields=["withdrawal"])

    withdrawal.result_desc = "Withdrawal request received and is being processed."
    withdrawal.save(update_fields=["result_desc"])
    send_withdrawal_processing_email(withdrawal)

    return withdrawal


# Kept as a compatibility alias for callers that used the previous service name.
verify_and_disburse = verify_and_create_withdrawal


@transaction.atomic
def approve_manual_withdrawal(withdrawal_id):
    withdrawal = WithdrawalRequest.objects.select_for_update().select_related("profile__user").get(pk=withdrawal_id)
    if withdrawal.status not in (WithdrawalRequest.Status.PENDING, WithdrawalRequest.Status.PROCESSING):
        raise MpesaError("This withdrawal has already been resolved.")

    withdrawal.status = WithdrawalRequest.Status.APPROVED
    withdrawal.result_desc = "Withdrawal processed and sent."
    withdrawal.processed_at = timezone.now()
    withdrawal.save(update_fields=["status", "result_desc", "processed_at"])
    send_withdrawal_approved_email(withdrawal)
    return withdrawal


@transaction.atomic
def reject_manual_withdrawal(withdrawal_id, reason=""):
    withdrawal = WithdrawalRequest.objects.select_for_update().select_related("profile__user").get(pk=withdrawal_id)
    if withdrawal.status not in (WithdrawalRequest.Status.PENDING, WithdrawalRequest.Status.PROCESSING):
        raise MpesaError("This withdrawal has already been resolved.")

    reason = (reason or "").strip() or "The withdrawal request was rejected."
    withdrawal.status = WithdrawalRequest.Status.REJECTED
    withdrawal.result_desc = reason
    withdrawal.processed_at = timezone.now()
    withdrawal.save(update_fields=["status", "result_desc", "processed_at"])
    send_withdrawal_rejected_email(withdrawal)
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
