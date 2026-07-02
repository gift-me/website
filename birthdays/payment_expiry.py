"""Expire stale pending M-Pesa payments."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import MpesaPayment

EXPIRED_MESSAGE = "Payment timed out. Please try again."


def pending_expiry_minutes():
    return int(getattr(settings, "PAYMENT_PENDING_EXPIRY_MINUTES", 15))


def expire_stale_pending_payments(profile_id=None):
    cutoff = timezone.now() - timedelta(minutes=pending_expiry_minutes())
    qs = MpesaPayment.objects.filter(
        status=MpesaPayment.Status.PENDING,
        created_at__lt=cutoff,
    )
    if profile_id is not None:
        qs = qs.filter(profile_id=profile_id)
    return qs.update(
        status=MpesaPayment.Status.FAILED,
        result_desc=EXPIRED_MESSAGE,
    )
