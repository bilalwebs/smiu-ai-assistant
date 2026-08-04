"""Email service tests (Milestone 3).

Covers the dev-email-sink behavior (SMTP disabled) and SMTP sending behavior.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.config.settings import TestingSettings
from app.services.email import EmailService


@pytest.fixture()
def settings() -> TestingSettings:
    return TestingSettings()


@pytest.fixture()
def email_service(settings: TestingSettings) -> EmailService:
    return EmailService(settings)


async def test_dev_sink_logs_email_when_smtp_disabled(
    email_service: EmailService,
) -> None:
    """When smtp_enabled is False, emails are logged but not sent."""
    await email_service.send_verification_email(
        email="test@example.com",
        full_name="Test User",
        token="test-token-123",
    )


async def test_dev_sink_logs_password_reset_when_smtp_disabled(
    email_service: EmailService,
) -> None:
    """When smtp_enabled is False, password reset emails are logged."""
    await email_service.send_password_reset_email(
        email="test@example.com",
        full_name="Test User",
        token="test-token-456",
    )


@patch("app.services.email.aiosmtplib.send", new_callable=AsyncMock)
async def test_smtp_sends_verification_email(
    mock_send: AsyncMock,
) -> None:
    """When smtp_enabled is True, the email is sent via aiosmtplib."""
    settings = TestingSettings(
        smtp_enabled=True, smtp_user="user@gmail.com", smtp_password="app-password"
    )
    service = EmailService(settings)
    await service.send_verification_email(
        email="test@example.com",
        full_name="Test User",
        token="test-token-123",
    )
    mock_send.assert_called_once()
    message = mock_send.call_args[0][0]
    assert message["To"] == "test@example.com"
    assert "Verify" in message["Subject"]


@patch("app.services.email.aiosmtplib.send", new_callable=AsyncMock)
async def test_smtp_sends_password_reset_email(
    mock_send: AsyncMock,
) -> None:
    """When smtp_enabled is True, password reset emails are sent."""
    settings = TestingSettings(
        smtp_enabled=True, smtp_user="user@gmail.com", smtp_password="app-password"
    )
    service = EmailService(settings)
    await service.send_password_reset_email(
        email="test@example.com",
        full_name="Test User",
        token="test-token-456",
    )
    mock_send.assert_called_once()
    message = mock_send.call_args[0][0]
    assert message["To"] == "test@example.com"
    assert "Reset" in message["Subject"]


@patch("app.services.email.aiosmtplib.send", new_callable=AsyncMock)
async def test_smtp_failure_does_not_raise(
    mock_send: AsyncMock,
) -> None:
    """SMTP failures are logged but never fatal."""
    import aiosmtplib

    mock_send.side_effect = aiosmtplib.SMTPException("Connection refused")
    settings = TestingSettings(
        smtp_enabled=True, smtp_user="user@gmail.com", smtp_password="app-password"
    )
    service = EmailService(settings)
    await service.send_verification_email(
        email="test@example.com",
        full_name="Test User",
        token="test-token",
    )


@patch("app.services.email.aiosmtplib.send", new_callable=AsyncMock)
async def test_smtp_uses_configured_from_address(
    mock_send: AsyncMock,
) -> None:
    """The From address uses smtp_from when set."""
    settings = TestingSettings(
        smtp_enabled=True,
        smtp_user="user@gmail.com",
        smtp_password="app-password",
        smtp_from="noreply@smiu.edu",
    )
    service = EmailService(settings)
    await service.send_verification_email(
        email="test@example.com",
        full_name="Test User",
        token="test-token",
    )
    message = mock_send.call_args[0][0]
    assert message["From"] == "noreply@smiu.edu"


@patch("app.services.email.aiosmtplib.send", new_callable=AsyncMock)
async def test_smtp_falls_back_to_smtp_user_for_from(
    mock_send: AsyncMock,
) -> None:
    """When smtp_from is not set, falls back to smtp_user."""
    settings = TestingSettings(
        smtp_enabled=True,
        smtp_user="user@gmail.com",
        smtp_password="app-password",
    )
    service = EmailService(settings)
    await service.send_verification_email(
        email="test@example.com",
        full_name="Test User",
        token="test-token",
    )
    message = mock_send.call_args[0][0]
    assert message["From"] == "user@gmail.com"
