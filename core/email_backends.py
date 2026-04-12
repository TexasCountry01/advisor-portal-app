"""
Custom email backend for the TEST server.

Only delivers emails to whitelisted domains/addresses.
Emails to real member addresses are silently dropped (logged, not sent).
This prevents test server activity from reaching real clients.

Usage in .env:
    EMAIL_BACKEND=core.email_backends.TestSafeEmailBackend
    EMAIL_SAFE_DOMAINS=profeds.com,sbcglobal.net
"""
import logging

from django.core.mail.backends.smtp import EmailBackend as SMTPBackend
from django.conf import settings

logger = logging.getLogger('core.email')

# Domains that are safe to send to from the test server
DEFAULT_SAFE_DOMAINS = ['profeds.com', 'sbcglobal.net']


class TestSafeEmailBackend(SMTPBackend):
    """
    SMTP backend that filters recipients to only allow whitelisted domains.
    Emails to non-whitelisted addresses are logged and dropped.
    """

    def _get_safe_domains(self):
        raw = getattr(settings, 'EMAIL_SAFE_DOMAINS', None)
        if raw:
            if isinstance(raw, str):
                return [d.strip().lower() for d in raw.split(',') if d.strip()]
            return [d.lower() for d in raw]
        return DEFAULT_SAFE_DOMAINS

    def _is_safe(self, email):
        safe_domains = self._get_safe_domains()
        domain = email.strip().lower().split('@')[-1]
        return domain in safe_domains

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        sent_count = 0
        for message in email_messages:
            original_to = list(message.to or [])
            original_cc = list(message.cc or [])
            original_bcc = list(message.bcc or [])

            safe_to = [e for e in original_to if self._is_safe(e)]
            safe_cc = [e for e in original_cc if self._is_safe(e)]
            safe_bcc = [e for e in original_bcc if self._is_safe(e)]

            dropped_to = [e for e in original_to if not self._is_safe(e)]
            dropped_cc = [e for e in original_cc if not self._is_safe(e)]
            dropped_bcc = [e for e in original_bcc if not self._is_safe(e)]

            all_dropped = dropped_to + dropped_cc + dropped_bcc
            if all_dropped:
                logger.info(
                    f'[TestSafeEmailBackend] Dropped non-safe recipients from '
                    f'"{message.subject}": {", ".join(all_dropped)}'
                )

            if not safe_to and not safe_cc and not safe_bcc:
                logger.info(
                    f'[TestSafeEmailBackend] Skipping email "{message.subject}" — '
                    f'no safe recipients remain after filtering.'
                )
                continue

            message.to = safe_to
            message.cc = safe_cc
            message.bcc = safe_bcc

            sent_count += super().send_messages([message])

        return sent_count
