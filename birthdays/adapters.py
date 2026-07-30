from allauth.account.adapter import DefaultAccountAdapter
import logging

logger = logging.getLogger(__name__)


class AccountAdapter(DefaultAccountAdapter):
    """GiftMe account adapter with clearer email failure logging."""

    def send_mail(self, template_prefix, email, context):
        try:
            return super().send_mail(template_prefix, email, context)
        except Exception:
            logger.exception("Failed sending account email template=%s to=%s", template_prefix, email)
            raise
