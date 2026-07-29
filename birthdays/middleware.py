import logging
import traceback

from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger(__name__)


class AjaxJsonErrorMiddleware:
    """
    Convert HTML error pages into JSON for XHR/fetch requests so signup/login
    clients never choke on "<html>... is not valid JSON".
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not self._wants_json(request):
            return response
        if self._is_json_response(response):
            return response
        if response.status_code < 400:
            return response

        reason = self._default_reason(response.status_code)
        payload = {
            "success": False,
            "errors": {"__all__": [reason]},
            "status": response.status_code,
        }
        if settings.DEBUG:
            snippet = ""
            try:
                snippet = response.content.decode("utf-8", errors="replace")[:800]
            except Exception:
                snippet = ""
            payload["debug"] = {
                "reason": reason,
                "content_type": response.get("Content-Type", ""),
                "body_snippet": snippet,
            }
        return JsonResponse(payload, status=response.status_code)

    def process_exception(self, request, exception):
        if not self._wants_json(request):
            return None
        logger.exception("Unhandled error on %s %s", request.method, request.path)
        message = str(exception) if settings.DEBUG else "Server error. Please try again shortly."
        payload = {
            "success": False,
            "errors": {"__all__": [message]},
            "status": 500,
        }
        if settings.DEBUG:
            payload["debug"] = {
                "type": type(exception).__name__,
                "detail": str(exception),
                "traceback": traceback.format_exc()[:4000],
            }
        return JsonResponse(payload, status=500)

    @staticmethod
    def _wants_json(request):
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return True
        accept = request.headers.get("Accept", "")
        return "application/json" in accept

    @staticmethod
    def _is_json_response(response):
        return "application/json" in (response.get("Content-Type") or "")

    @staticmethod
    def _default_reason(status_code):
        if status_code == 403:
            return "Security check failed. Refresh the page and try again."
        if status_code == 404:
            return "The requested page was not found."
        if status_code >= 500:
            return "Server error. Please try again shortly."
        return "Request failed. Please try again."
