import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .exceptions import MpesaError
from .models import MpesaPayment, UserProfile
from .mpesa import get_mpesa_client
from .payment_service import initiate_mpesa_payment, mark_payment_completed, mark_payment_failed, payment_status_payload

logger = logging.getLogger(__name__)


def _json_error(message, status=400):
    return JsonResponse({"success": False, "error": message}, status=status)


@require_POST
def stk_push_initiate(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _json_error("Invalid request.")

    page_type = payload.get("page_type", "gift")
    slug = (payload.get("slug") or "").strip()

    if page_type == "wishlist":
        profile = UserProfile.objects.filter(wishlist_slug=slug).first()
    else:
        profile = UserProfile.objects.filter(gift_slug=slug).first()

    if not profile:
        return _json_error("Page not found.", 404)

    try:
        payment = initiate_mpesa_payment(
            profile=profile,
            gift_id=(payload.get("gift_id") or "").strip() or None,
            wishlist_item_id=(payload.get("wishlist_item_id") or "").strip() or None,
            amount_raw=payload.get("amount"),
            sender_name=payload.get("sender_name", ""),
            payer_phone=payload.get("payer_phone", ""),
            message=payload.get("message", ""),
        )
    except MpesaError as exc:
        return _json_error(str(exc))

    return JsonResponse(
        {
            "success": True,
            "payment_id": str(payment.pk),
            "status": payment.status,
            "message": "STK prompt sent. Check your phone to complete payment.",
        }
    )


@require_GET
def payment_status(request, payment_id):
    payment = MpesaPayment.objects.filter(pk=payment_id).select_related("profile", "wishlist_item", "catalog_gift").first()
    if not payment:
        return _json_error("Payment not found.", 404)

    if payment.status == MpesaPayment.Status.PENDING and payment.checkout_request_id:
        try:
            client = get_mpesa_client()
            query = client.stk_query(payment.checkout_request_id)
            if f"{query.get('ResultCode', '')}" == "0":
                mark_payment_completed(payment, result_desc=query.get("ResultDesc", "Success"))
            elif f"{query.get('ResultCode', '')}" not in ("", "1032"):
                mark_payment_failed(payment, query.get("ResultDesc", "Payment failed."))
        except MpesaError:
            pass
        payment.refresh_from_db()

    return JsonResponse({"success": True, **payment_status_payload(payment, request)})


@csrf_exempt
@require_POST
def mpesa_callback(request):
    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        logger.warning("M-Pesa callback invalid JSON")
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

    parsed = get_mpesa_client().parse_stk_callback(body)
    checkout_id = parsed.get("checkout_request_id")

    if not checkout_id:
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

    payment = MpesaPayment.objects.filter(checkout_request_id=checkout_id).first()
    if not payment:
        logger.warning("M-Pesa callback for unknown CheckoutRequestID: %s", checkout_id)
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

    if parsed.get("success"):
        mark_payment_completed(
            payment,
            mpesa_receipt=parsed.get("mpesa_receipt", ""),
            result_desc=parsed.get("result_desc", "Success"),
        )
    else:
        mark_payment_failed(payment, parsed.get("result_desc", "Payment failed or cancelled."))

    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
