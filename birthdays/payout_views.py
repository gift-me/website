import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .exceptions import MpesaError
from .models import Payout, UserProfile
from .mpesa import MpesaClient, get_mpesa_client
from .safe_cache import cache_get, cache_set
from .payout_service import (
    find_payout_for_b2c_callback,
    initiate_payout_authorization,
    mark_payout_completed,
    mark_payout_failed,
    payout_status_payload,
    verify_and_disburse,
)

logger = logging.getLogger(__name__)


def _json_error(message, status=400):
    return JsonResponse({"success": False, "error": message}, status=status)


def _profile_for_request(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return profile


@login_required
@require_POST
def payout_initiate(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_error("Invalid request.")

    profile = _profile_for_request(request)
    try:
        authorization = initiate_payout_authorization(
            profile=profile,
            amount_raw=payload.get("amount"),
            payout_phone_raw=payload.get("payout_phone"),
        )
    except MpesaError as exc:
        return _json_error(str(exc))

    return JsonResponse(
        {
            "success": True,
            "authorization_id": str(authorization.pk),
            "message": f"Verification code sent to {request.user.email}.",
            "expires_at": authorization.expires_at.isoformat(),
        }
    )


@login_required
@require_POST
def payout_verify(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_error("Invalid request.")

    profile = _profile_for_request(request)
    try:
        payout = verify_and_disburse(
            profile=profile,
            authorization_id=payload.get("authorization_id"),
            code_raw=payload.get("code"),
        )
    except MpesaError as exc:
        return _json_error(str(exc))

    return JsonResponse(
        {
            "success": True,
            "message": "Payout submitted. M-Pesa is processing your transfer.",
            **payout_status_payload(payout),
        }
    )


@login_required
@require_GET
def payout_status(request, payout_id):
    profile = _profile_for_request(request)
    payout = Payout.objects.filter(
        pk=payout_id, profile=profile, kind=Payout.Kind.USER
    ).first()
    if not payout:
        return _json_error("Payout not found.", 404)

    # Late-callback recovery: ask Daraja for status; result still lands on ResultURL.
    if payout.status == Payout.Status.PROCESSING and (
        payout.mpesa_transaction_id or payout.originator_conversation_id
    ):
        min_age = getattr(settings, "B2C_QUERY_MIN_AGE_SECONDS", 45)
        throttle_key = f"mpesa_b2c_query_last:{payout.pk}"
        if not cache_get(throttle_key):
            from datetime import timedelta

            from django.utils import timezone

            if timezone.now() - payout.created_at >= timedelta(seconds=min_age):
                try:
                    get_mpesa_client().transaction_status_query(
                        transaction_id=payout.mpesa_transaction_id,
                        originator_conversation_id=payout.originator_conversation_id,
                        occasion=f"payout:{payout.pk}",
                    )
                except MpesaError:
                    logger.exception("B2C status query failed for payout %s", payout.pk)
                cache_set(throttle_key, 1, timeout=30)
        payout.refresh_from_db()

    return JsonResponse({"success": True, **payout_status_payload(payout)})


def _handle_b2c_callback(body):
    parsed = MpesaClient.parse_b2c_result(body)
    payout = find_payout_for_b2c_callback(parsed)

    if not payout:
        logger.warning(
            "B2C callback for unknown conversation: originator=%s conversation=%s occasion=%s",
            parsed.get("originator_conversation_id"),
            parsed.get("conversation_id"),
            parsed.get("occasion"),
        )
        return

    if parsed.get("success"):
        mark_payout_completed(
            payout,
            transaction_id=parsed.get("transaction_id", ""),
            result_desc=parsed.get("result_desc", "Payout completed."),
        )
    else:
        mark_payout_failed(payout, parsed.get("result_desc", "Payout failed."))


@csrf_exempt
@require_POST
def b2c_result_callback(request):
    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        logger.warning("B2C result callback invalid JSON")
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

    _handle_b2c_callback(body)
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})


@csrf_exempt
@require_POST
def b2c_timeout_callback(request):
    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        logger.warning("B2C timeout callback invalid JSON")
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

    parsed = MpesaClient.parse_b2c_result(body)
    payout = find_payout_for_b2c_callback(parsed)

    if payout and payout.status == Payout.Status.PROCESSING:
        mark_payout_failed(
            payout,
            parsed.get("result_desc") or "M-Pesa queue timeout. Check your phone or try again.",
        )

    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
