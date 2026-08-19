import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .exceptions import MpesaError
from .models import UserProfile, WithdrawalRequest
from .mpesa import MpesaClient
from .withdrawal_service import (
    initiate_withdrawal_authorization,
    mark_withdrawal_completed,
    mark_withdrawal_failed,
    verify_and_create_withdrawal,
    withdrawal_status_payload,
)

logger = logging.getLogger(__name__)


def _json_error(message, status=400):
    return JsonResponse({"success": False, "error": message}, status=status)


def _profile_for_request(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return profile


@login_required
@require_POST
def withdraw_initiate(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_error("Invalid request.")

    profile = _profile_for_request(request)
    try:
        authorization = initiate_withdrawal_authorization(
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
def withdraw_verify(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_error("Invalid request.")

    profile = _profile_for_request(request)
    try:
        withdrawal = verify_and_create_withdrawal(
            profile=profile,
            authorization_id=payload.get("authorization_id"),
            code_raw=payload.get("code"),
        )
    except MpesaError as exc:
        return _json_error(str(exc))

    return JsonResponse(
        {
            "success": True,
            "message": "Your withdrawal is being processed. It normally takes up to 24 hours. We will email you when it has been processed.",
            **withdrawal_status_payload(withdrawal),
        }
    )


@login_required
@require_GET
def withdraw_status(request, withdrawal_id):
    profile = _profile_for_request(request)
    withdrawal = WithdrawalRequest.objects.filter(pk=withdrawal_id, profile=profile).first()
    if not withdrawal:
        return _json_error("Withdrawal not found.", 404)

    return JsonResponse({"success": True, **withdrawal_status_payload(withdrawal)})


def _handle_b2c_callback(body):
    parsed = MpesaClient.parse_b2c_result(body)
    originator_id = parsed.get("originator_conversation_id")
    conversation_id = parsed.get("conversation_id")

    withdrawal = None
    if originator_id:
        withdrawal = WithdrawalRequest.objects.filter(originator_conversation_id=originator_id).first()
    if not withdrawal and conversation_id:
        withdrawal = WithdrawalRequest.objects.filter(conversation_id=conversation_id).first()

    if not withdrawal:
        logger.warning(
            "B2C callback for unknown conversation: originator=%s conversation=%s",
            originator_id,
            conversation_id,
        )
        return

    if parsed.get("success"):
        mark_withdrawal_completed(
            withdrawal,
            transaction_id=parsed.get("transaction_id", ""),
            result_desc=parsed.get("result_desc", "Withdrawal completed."),
        )
    else:
        mark_withdrawal_failed(withdrawal, parsed.get("result_desc", "Withdrawal failed."))


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
    originator_id = parsed.get("originator_conversation_id")
    conversation_id = parsed.get("conversation_id")

    withdrawal = None
    if originator_id:
        withdrawal = WithdrawalRequest.objects.filter(originator_conversation_id=originator_id).first()
    if not withdrawal and conversation_id:
        withdrawal = WithdrawalRequest.objects.filter(conversation_id=conversation_id).first()

    if withdrawal and withdrawal.status == WithdrawalRequest.Status.PROCESSING:
        mark_withdrawal_failed(
            withdrawal,
            parsed.get("result_desc") or "M-Pesa queue timeout. Check your phone or try again.",
        )

    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
