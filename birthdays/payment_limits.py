"""Redis-backed rate limits for STK initiation."""

from django.conf import settings

from .exceptions import MpesaError
from .models import MpesaPayment
from .safe_cache import cache_add, cache_incr, cache_set


def _increment_counter(key, window_seconds):
    if cache_add(key, 1, timeout=window_seconds):
        return 1
    count = cache_incr(key)
    if count is None:
        cache_set(key, 1, timeout=window_seconds)
        return 1
    return count


def check_stk_rate_limits(ip_address, phone, profile_id):
    ip_limit = getattr(settings, "STK_IP_LIMIT", 10)
    ip_window = getattr(settings, "STK_IP_WINDOW", 60)
    phone_limit = getattr(settings, "STK_PHONE_LIMIT", 5)
    phone_window = getattr(settings, "STK_PHONE_WINDOW", 3600)
    max_pending = getattr(settings, "STK_MAX_PENDING_PER_PHONE_PROFILE", 3)

    if ip_address:
        ip_key = f"stk_limit:ip:{ip_address}"
        if _increment_counter(ip_key, ip_window) > ip_limit:
            raise MpesaError("Too many payment attempts. Please wait a minute and try again.")

    phone_key = f"stk_limit:phone:{phone}"
    if _increment_counter(phone_key, phone_window) > phone_limit:
        raise MpesaError("Too many payment attempts for this number. Please try again later.")

    profile_limit = getattr(settings, "STK_PROFILE_LIMIT", 100)
    profile_window = getattr(settings, "STK_PROFILE_WINDOW", 3600)
    profile_key = f"stk_limit:profile:{profile_id}"
    if _increment_counter(profile_key, profile_window) > profile_limit:
        raise MpesaError(
            "This page is receiving a lot of gifts right now. Please try again in a few minutes."
        )

    pending = MpesaPayment.objects.filter(
        payer_phone=phone,
        profile_id=profile_id,
        status=MpesaPayment.Status.PENDING,
    ).count()
    if pending >= max_pending:
        raise MpesaError(
            "You already have pending payments on this page. "
            "Complete them on your phone or wait a few minutes."
        )
