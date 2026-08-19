"""Idempotent payment initiation via Redis + database."""

from .models import MpesaPayment, PaymentAttempt
from .safe_cache import cache_get, cache_set

IDEMPOTENCY_CACHE_TTL = 3600


def resolve_idempotent_payment(idempotency_key):
    key = (idempotency_key or "").strip()
    if not key:
        return None

    cache_key = f"idempotency:{key}"
    payment_id = cache_get(cache_key)
    if payment_id:
        payment = MpesaPayment.objects.filter(pk=payment_id).select_related("profile").first()
        if payment:
            return payment

    attempt = PaymentAttempt.objects.select_related("payment__profile").filter(idempotency_key=key).first()
    if not attempt:
        return None

    cache_set(cache_key, attempt.payment_id, timeout=IDEMPOTENCY_CACHE_TTL)
    return attempt.payment


def remember_idempotent_payment(idempotency_key, payment_id):
    key = (idempotency_key or "").strip()
    if key and payment_id:
        cache_set(f"idempotency:{key}", payment_id, timeout=IDEMPOTENCY_CACHE_TTL)
