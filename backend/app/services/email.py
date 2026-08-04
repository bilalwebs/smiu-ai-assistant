"""Transactional email service (Milestone 3).

Purpose:
    Send the account lifecycle emails (email verification and password reset)
    over Gmail SMTP using ``aiosmtplib``. Every message carries both a plain
    text and an HTML alternative. In development and test environments SMTP is
    disabled by default and messages are logged instead (the development
    email sink), so account flows never depend on an external mail server being
    reachable; production enables SMTP with Gmail App Password credentials.

Responsibilities:
    - Build and send the email-verification message from its template.
    - Build and send the password-reset message from its template.
    - Degrade gracefully: when ``smtp_enabled`` is false, log the message body
      (dev/test) instead of sending; failures are logged, never fatal.
"""

from __future__ import annotations

import logging
from email.message import EmailMessage

import aiosmtplib

from app.config.settings import Settings
from app.services.email_templates import (
    EmailContent,
    render_password_reset_email,
    render_verification_email,
)

logger = logging.getLogger(__name__)


class EmailService:
    """Sends transactional emails using the configured SMTP settings."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def send_verification_email(
        self, *, email: str, full_name: str, token: str
    ) -> None:
        """Email the signed verification link for ``email``."""
        link = f"{self._settings.frontend_base_url}/verify-email?token={token}"
        content = render_verification_email(
            full_name=full_name,
            link=link,
            expires_minutes=self._settings.email_verification_expire_minutes,
        )
        await self._send(email=email, content=content)

    async def send_password_reset_email(
        self, *, email: str, full_name: str, token: str
    ) -> None:
        """Email the signed password-reset link for ``email``."""
        base = self._settings.frontend_base_url.rstrip("/")
        path = self._settings.frontend_reset_path.strip("/")
        link = f"{base}/{path}?token={token}"
        content = render_password_reset_email(
            full_name=full_name,
            link=link,
            expires_minutes=self._settings.password_reset_expire_minutes,
        )
        await self._send(email=email, content=content)

    async def _send(self, *, email: str, content: EmailContent) -> None:
        if not self._settings.smtp_enabled:
            logger.info(
                "SMTP disabled; email would be sent to %s (subject=%r):\n%s",
                email,
                content.subject,
                content.text,
            )
            return
        message = EmailMessage()
        message["From"] = self._settings.smtp_from or self._settings.smtp_user or ""
        message["To"] = email
        message["Subject"] = content.subject
        message.set_content(content.text)
        message.add_alternative(content.html, subtype="html")
        try:
            await aiosmtplib.send(
                message,
                hostname=self._settings.smtp_host,
                port=self._settings.smtp_port,
                username=self._settings.smtp_user,
                password=self._settings.smtp_password,
                start_tls=self._settings.smtp_starttls,
                use_tls=False,
                timeout=10,
            )
        except aiosmtplib.SMTPException:
            logger.exception("Failed to send email to %s", email)
