"""
Safaricom Daraja M-Pesa STK Push (Lipa na M-Pesa Online) client.

Sandbox docs: https://developer.safaricom.co.ke/APIs/MpesaExpressSimulate
"""

import base64
import json
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

import requests
from django.conf import settings

from .conversions import whole_number
from .exceptions import MpesaError

logger = logging.getLogger(__name__)


def normalize_callback_url(url):
    """Validate and normalize the Daraja STK callback URL."""
    callback = (url or "").strip()
    if not callback:
        raise MpesaError(
            "MPESA_CALLBACK_URL is not set. Add your HTTPS callback URL to .env and restart the server."
        )

    parsed = urlparse(callback)
    if parsed.scheme != "https" or not parsed.netloc:
        raise MpesaError("MPESA_CALLBACK_URL must be a full HTTPS URL (use ngrok for local sandbox).")

    host = parsed.netloc.split(":")[0]
    if "." not in host:
        raise MpesaError(
            f"MPESA_CALLBACK_URL host looks incomplete ({host}). "
            "Use your full ngrok URL, e.g. https://your-subdomain.ngrok-free.dev/api/mpesa/callback/"
        )

    path = parsed.path.rstrip("/") or "/api/mpesa/callback"
    if not path.endswith("/api/mpesa/callback"):
        logger.warning("MPESA_CALLBACK_URL path is %s; expected /api/mpesa/callback", parsed.path)

    return f"https://{parsed.netloc}{path}/"


def derive_b2c_callback_url(stk_callback_url, suffix):
    """Build B2C result/timeout URLs from the STK callback base URL."""
    normalized = normalize_callback_url(stk_callback_url)
    base = normalized.rstrip("/").rsplit("/api/mpesa/callback", 1)[0]
    return f"{base}/api/mpesa/b2c/{suffix}/"


def parse_b2c_result(body):
    """Parse Daraja B2C ResultURL / QueueTimeOutURL callback body."""
    result = (body or {}).get("Result", {})
    parameters = {}
    for item in result.get("ResultParameters", {}).get("ResultParameter", []):
        key = item.get("Key")
        if key:
            parameters[key] = item.get("Value")

    result_code = result.get("ResultCode")
    return {
        "result_type": result.get("ResultType"),
        "result_code": result_code,
        "result_desc": result.get("ResultDesc", ""),
        "success": f"{result_code}" == "0",
        "originator_conversation_id": result.get("OriginatorConversationID", ""),
        "conversation_id": result.get("ConversationID", ""),
        "transaction_id": result.get("TransactionID", "") or parameters.get("TransactionReceipt", ""),
        "amount": parameters.get("TransactionAmount"),
        "receiver_party": parameters.get("ReceiverPartyPublicName"),
    }


def normalize_phone(phone):
    """Normalize Kenyan numbers to 254XXXXXXXXX."""
    digits = "".join(c for c in f"{phone}" if c.isdigit())
    if digits.startswith("254") and len(digits) == 12:
        return digits
    if digits.startswith("0") and len(digits) == 10:
        return "254" + digits[1:]
    if len(digits) == 9 and digits[:1] in ("7", "1"):
        return "254" + digits
    raise MpesaError("Enter a valid Kenyan M-Pesa number (e.g. 0712345678).")


def parse_stk_callback(body):
    """
    Parse Daraja STK callback body.

    Returns dict with keys:
      checkout_request_id, merchant_request_id, result_code,
      result_desc, success, amount, mpesa_receipt, phone
    """
    callback = (body or {}).get("Body", {}).get("stkCallback", {})
    result_code = callback.get("ResultCode")
    metadata = {}
    for item in callback.get("CallbackMetadata", {}).get("Item", []):
        metadata[item.get("Name")] = item.get("Value")

    return {
        "checkout_request_id": callback.get("CheckoutRequestID", ""),
        "merchant_request_id": callback.get("MerchantRequestID", ""),
        "result_code": result_code,
        "result_desc": callback.get("ResultDesc", ""),
        "success": f"{result_code}" == "0",
        "amount": metadata.get("Amount"),
        "mpesa_receipt": metadata.get("MpesaReceiptNumber", ""),
        "phone": metadata.get("PhoneNumber"),
        "transaction_date": metadata.get("TransactionDate"),
    }


def _parse_whole_kes_amount(amount):
    """Return a whole-number KES amount suitable for Daraja JSON payloads."""
    try:
        amount_kes = Decimal(f"{amount}")
    except InvalidOperation as exc:
        raise MpesaError("Amount must be at least KES 1.") from exc

    if amount_kes < 1 or amount_kes != amount_kes.to_integral_value():
        raise MpesaError("Amount must be at least KES 1.")

    return whole_number(amount_kes)


class MpesaClient:
    """Minimal Daraja API client for OAuth + STK Push + B2C."""

    format_phone = staticmethod(normalize_phone)
    parse_stk_callback = staticmethod(parse_stk_callback)
    parse_b2c_result = staticmethod(parse_b2c_result)

    def __init__(self):
        self.base_url = settings.MPESA_BASE_URL.rstrip("/")
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.shortcode = settings.MPESA_SHORTCODE
        self.till = settings.MPESA_TILL
        self.passkey = settings.MPESA_PASSKEY
        self.callback_url = normalize_callback_url(settings.MPESA_CALLBACK_URL)
        self.transaction_type = settings.MPESA_TRANSACTION_TYPE
        self.b2c_shortcode = settings.MPESA_B2C_SHORTCODE or self.shortcode
        self.b2c_initiator = settings.MPESA_B2C_INITIATOR_NAME
        self.b2c_security_credential = settings.MPESA_B2C_SECURITY_CREDENTIAL
        self.b2c_command_id = settings.MPESA_B2C_COMMAND_ID
        self.b2c_result_url = settings.MPESA_B2C_RESULT_URL or derive_b2c_callback_url(
            settings.MPESA_CALLBACK_URL, "result"
        )
        self.b2c_timeout_url = settings.MPESA_B2C_TIMEOUT_URL or derive_b2c_callback_url(
            settings.MPESA_CALLBACK_URL, "timeout"
        )

    def _headers(self, access_token):
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def get_access_token(self):
        from .safe_cache import cache_get, cache_set

        cached = cache_get("daraja:oauth_token")
        if cached:
            return cached

        if not self.consumer_key or not self.consumer_secret:
            raise MpesaError("MPESA_CONSUMER_KEY and MPESA_CONSUMER_SECRET are required.")

        logger.debug("[MPESA_OAUTH_REQUEST] env=%s base_url=%s", settings.MPESA_ENV, self.base_url)
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        try:
            response = requests.get(
                url,
                auth=(self.consumer_key, self.consumer_secret),
                timeout=30,
            )
        except requests.RequestException as exc:
            raise MpesaError("Could not connect to M-Pesa. Please try again.") from exc
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise MpesaError("Invalid OAuth response from Daraja.", response.text) from exc

        if response.status_code != 200 or "access_token" not in data:
            logger.debug("[MPESA_OAUTH_ERROR] status=%s data=%s", response.status_code, data)
            raise MpesaError(
                data.get("errorMessage") or data.get("error") or "Failed to obtain M-Pesa access token.",
                data,
            )
        token = data["access_token"]
        cache_set("daraja:oauth_token", token, timeout=3300)
        return token

    def _password_payload(self, timestamp):
        raw = f"{self.shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(raw.encode()).decode()

    def stk_push(self, phone, amount, account_reference, transaction_desc):
        """
        Initiate STK Push. Returns Daraja response dict on acceptance.

        amount: integer KES
        account_reference: max 12 chars (invoice / order ref)
        transaction_desc: short description shown to customer
        """
        if not self.shortcode or not self.passkey:
            raise MpesaError("MPESA_SHORTCODE and MPESA_PASSKEY are required.")

        amount = _parse_whole_kes_amount(amount)
        phone = normalize_phone(phone)
        logger.debug(
            "[MPESA_STK_REQUEST] callback=%s shortcode=%s phone=%s amount=%s",
            self.callback_url,
            self.shortcode,
            phone,
            amount,
        )
        access_token = self.get_access_token()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"

        party_b = self.till if self.till else self.shortcode
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": self._password_payload(timestamp),
            "Timestamp": timestamp,
            "TransactionType": self.transaction_type,
            "Amount": amount,
            "PartyA": phone,
            "PartyB": party_b,
            "PhoneNumber": phone,
            "CallBackURL": self.callback_url,
            "AccountReference": f"{account_reference}"[:12],
            "TransactionDesc": f"{transaction_desc}"[:30],
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._headers(access_token),
                timeout=30,
            )
        except requests.RequestException as exc:
            raise MpesaError("Could not connect to M-Pesa. Please try again.") from exc

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise MpesaError("Invalid STK Push response from Daraja.", response.text) from exc

        if response.status_code != 200:
            logger.debug("[MPESA_STK_HTTP_ERROR] status=%s data=%s", response.status_code, data)
            raise MpesaError(
                data.get("errorMessage") or data.get("error") or "STK Push request failed.",
                data,
            )

        if f"{data.get('ResponseCode', '')}" != "0":
            logger.debug("[MPESA_STK_REJECTED] %s", data)
            raise MpesaError(
                data.get("ResponseDescription") or data.get("CustomerMessage") or "STK Push rejected.",
                data,
            )

        return data

    def b2c_payment(self, phone, amount, remarks="GiftMe withdrawal", occasion="Withdrawal"):
        """Initiate B2C payment to a customer's M-Pesa number."""
        if not self.b2c_initiator or not self.b2c_security_credential:
            raise MpesaError(
                "MPESA_B2C_INITIATOR_NAME and MPESA_B2C_SECURITY_CREDENTIAL are required for withdrawals."
            )
        if not self.b2c_shortcode:
            raise MpesaError("MPESA_B2C_SHORTCODE is required for withdrawals.")

        amount = _parse_whole_kes_amount(amount)
        phone = normalize_phone(phone)
        logger.debug(
            "[MPESA_B2C_REQUEST] shortcode=%s phone=%s amount=%s",
            self.b2c_shortcode,
            phone,
            amount,
        )

        access_token = self.get_access_token()
        url = f"{self.base_url}/mpesa/b2c/v1/paymentrequest"
        payload = {
            "InitiatorName": self.b2c_initiator,
            "SecurityCredential": self.b2c_security_credential,
            "CommandID": self.b2c_command_id,
            "Amount": amount,
            "PartyA": self.b2c_shortcode,
            "PartyB": phone,
            "Remarks": f"{remarks}"[:100],
            "QueueTimeOutURL": self.b2c_timeout_url,
            "ResultURL": self.b2c_result_url,
            "Occasion": f"{occasion}"[:100],
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._headers(access_token),
                timeout=30,
            )
        except requests.RequestException as exc:
            raise MpesaError("Could not connect to M-Pesa. Please try again.") from exc

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise MpesaError("Invalid B2C response from Daraja.", response.text) from exc

        if response.status_code != 200:
            logger.debug("[MPESA_B2C_HTTP_ERROR] status=%s data=%s", response.status_code, data)
            raise MpesaError(
                data.get("errorMessage") or data.get("error") or "B2C payment request failed.",
                data,
            )

        if f"{data.get('ResponseCode', '')}" != "0":
            logger.debug("[MPESA_B2C_REJECTED] %s", data)
            raise MpesaError(
                data.get("ResponseDescription") or "B2C payment rejected.",
                data,
            )

        return data

    def stk_query(self, checkout_request_id):
        """Query Daraja for final status when callback is delayed/missed."""
        if not checkout_request_id:
            raise MpesaError("CheckoutRequestID is required for STK query.")

        access_token = self.get_access_token()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": self._password_payload(timestamp),
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id,
        }
        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._headers(access_token),
                timeout=30,
            )
        except requests.RequestException as exc:
            print(exc)
            raise MpesaError("Could not connect to M-Pesa. Please try again.") from exc
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise MpesaError("Invalid STK Query response from Daraja.", response.text) from exc

        if response.status_code != 200 or f"{data.get('ResponseCode', '')}" != "0":
            logger.debug("[MPESA_STK_QUERY_FAILED] %s", data)
            raise MpesaError(
                data.get("errorMessage")
                or data.get("error")
                or data.get("ResponseDescription")
                or "STK Query failed.",
                data,
            )
        return data


def get_mpesa_client():
    return MpesaClient()
