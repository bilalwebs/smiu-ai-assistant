"""Email template rendering tests (Milestone 3).

Covers verification and password-reset email template rendering for both
plain-text and HTML output.
"""

from __future__ import annotations

from app.services.email_templates import (
    render_password_reset_email,
    render_verification_email,
)


class TestVerificationEmail:
    """Tests for the email-verification template."""

    def test_returns_correct_subject(self) -> None:
        content = render_verification_email(
            full_name="Test User",
            link="http://localhost:3000/verify-email?token=abc123",
            expires_minutes=1440,
        )
        assert content.subject == "Verify your email address"

    def test_plain_text_contains_name(self) -> None:
        content = render_verification_email(
            full_name="Test User",
            link="http://localhost:3000/verify-email?token=abc123",
            expires_minutes=60,
        )
        assert "Test User" in content.text

    def test_plain_text_contains_link(self) -> None:
        link = "http://localhost:3000/verify-email?token=abc123"
        content = render_verification_email(
            full_name="User", link=link, expires_minutes=60
        )
        assert link in content.text

    def test_plain_text_contains_expiry(self) -> None:
        content = render_verification_email(
            full_name="User",
            link="http://example.com",
            expires_minutes=120,
        )
        assert "120" in content.text

    def test_html_contains_link(self) -> None:
        link = "http://localhost:3000/verify-email?token=abc123"
        content = render_verification_email(
            full_name="User", link=link, expires_minutes=60
        )
        assert link in content.html

    def test_html_is_valid_structure(self) -> None:
        content = render_verification_email(
            full_name="User",
            link="http://example.com",
            expires_minutes=60,
        )
        assert "<!DOCTYPE html>" in content.html
        assert "</html>" in content.html

    def test_html_escapes_name(self) -> None:
        content = render_verification_email(
            full_name="<script>alert('x')</script>",
            link="http://example.com",
            expires_minutes=60,
        )
        assert "<script>" not in content.html
        assert "&lt;script&gt;" in content.html

    def test_html_escapes_link(self) -> None:
        content = render_verification_email(
            full_name="User",
            link="http://example.com\"><script>alert(1)</script>",
            expires_minutes=60,
        )
        assert "<script>" not in content.html


class TestPasswordResetEmail:
    """Tests for the password-reset template."""

    def test_returns_correct_subject(self) -> None:
        content = render_password_reset_email(
            full_name="Test User",
            link="http://localhost:3000/reset-password?token=xyz789",
            expires_minutes=30,
        )
        assert content.subject == "Reset your password"

    def test_plain_text_contains_name(self) -> None:
        content = render_password_reset_email(
            full_name="Test User",
            link="http://localhost:3000/reset-password?token=xyz789",
            expires_minutes=30,
        )
        assert "Test User" in content.text

    def test_plain_text_contains_link(self) -> None:
        link = "http://localhost:3000/reset-password?token=xyz789"
        content = render_password_reset_email(
            full_name="User", link=link, expires_minutes=30
        )
        assert link in content.text

    def test_plain_text_contains_expiry(self) -> None:
        content = render_password_reset_email(
            full_name="User",
            link="http://example.com",
            expires_minutes=45,
        )
        assert "45" in content.text

    def test_plain_text_mentions_single_use(self) -> None:
        content = render_password_reset_email(
            full_name="User",
            link="http://example.com",
            expires_minutes=30,
        )
        assert "once" in content.text.lower()

    def test_html_contains_link(self) -> None:
        link = "http://localhost:3000/reset-password?token=xyz789"
        content = render_password_reset_email(
            full_name="User", link=link, expires_minutes=30
        )
        assert link in content.html

    def test_html_is_valid_structure(self) -> None:
        content = render_password_reset_email(
            full_name="User",
            link="http://example.com",
            expires_minutes=30,
        )
        assert "<!DOCTYPE html>" in content.html
        assert "</html>" in content.html

    def test_html_escapes_name(self) -> None:
        content = render_password_reset_email(
            full_name="<b>bold</b>",
            link="http://example.com",
            expires_minutes=30,
        )
        assert "<b>" not in content.html
        assert "&lt;b&gt;" in content.html

    def test_html_escapes_link(self) -> None:
        content = render_password_reset_email(
            full_name="User",
            link="http://example.com\"><img src=x onerror=alert(1)>",
            expires_minutes=30,
        )
        assert "<img" not in content.html
