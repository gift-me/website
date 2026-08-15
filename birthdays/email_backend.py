"""Brevo transactional email backend using HTTPS instead of SMTP."""

import base64
import logging
from email.utils import parseaddr

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


logger = logging.getLogger(__name__)


def _address(value):
    """Convert a Django email address into Brevo's name/email shape."""
    name, email = parseaddr(value or "")
    recipient = {"email": email}
    if name:
        recipient["name"] = name
    return recipient


class BrevoEmailBackend(BaseEmailBackend):
    """Send Django EmailMessage instances through Brevo's HTTPS API."""

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        sent = 0
        for message in email_messages:
            try:
                if self._send(message):
                    sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
                logger.exception("Brevo API email delivery failed")
        return sent

    def _send(self, message):
        recipients = [_address(value) for value in message.to if value]
        if not recipients:
            return False

        payload = {
            "sender": _address(message.from_email or settings.DEFAULT_FROM_EMAIL),
            "to": recipients,
            "subject": message.subject,
        }

        # Brevo accepts one inline body type. Prefer the HTML alternative when
        # Django/allauth supplies one; otherwise send the plain-text body.
        html_content = next(
            (content for content, mimetype in message.alternatives if mimetype == "text/html"),
            None,
        )
        if html_content:
            payload["htmlContent"] = html_content
        else:
            payload["textContent"] = message.body or ""

        if message.reply_to:
            payload["replyTo"] = _address(message.reply_to[0])

        if message.cc:
            payload["cc"] = [_address(value) for value in message.cc if value]
        if message.bcc:
            payload["bcc"] = [_address(value) for value in message.bcc if value]

        attachments = []
        for attachment in message.attachments:
            if isinstance(attachment, tuple):
                filename, content, _mimetype = attachment
            else:
                filename = attachment.name
                content = attachment.content
            if isinstance(content, str):
                content = content.encode("utf-8")
            attachments.append(
                {
                    "name": filename,
                    "content": base64.b64encode(content).decode("ascii"),
                }
            )
        if attachments:
            payload["attachment"] = attachments

        response = requests.post(
            settings.BREVO_API_URL,
            headers={
                "accept": "application/json",
                "api-key": settings.BREVO_API_KEY,
                "content-type": "application/json",
            },
            json=payload,
            timeout=settings.EMAIL_TIMEOUT,
        )
        try:
            response.raise_for_status()
        except requests.RequestException:
            logger.error(
                "Brevo API rejected email: status=%s body=%s",
                response.status_code,
                response.text[:1000],
            )
            raise
        return True
