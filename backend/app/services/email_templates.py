"""Transactional email templates (Milestone 3).

Purpose:
    Pure rendering functions for the account lifecycle emails — email
    verification and password reset. Every template returns both a plain-text
    and an HTML representation of the same message (HTML multipart with a
    plain-text fallback, per milestone scope). No templating dependency is
    required; user-provided values are HTML-escaped before interpolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

_BRAND = "SMU AI Assistant"


@dataclass(frozen=True)
class EmailContent:
    """Rendered email: subject plus plain-text and HTML bodies."""

    subject: str
    text: str
    html: str


def _action_link_html(label: str, link: str) -> str:
    """Render a single prominent call-to-action button link."""
    safe_label = escape(label)
    safe_link = escape(link)
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" '
        'style="margin: 24px 0;"><tr><td style="border-radius:6px;'
        'background:#1f6feb;padding:12px 24px;">'
        f'<a href="{safe_link}" '
        'style="color:#ffffff;text-decoration:none;font-weight:600;'
        f'font-family:Arial,sans-serif;">{safe_label}</a>'
        "</td></tr></table>"
    )


def _layout(title: str, heading: str, body_html: str) -> str:
    """Wrap a heading and body in a shared, inline-styled email shell."""
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        f"<title>{escape(title)}</title></head>"
        '<body style="margin:0;padding:0;'
        'background:#f4f5f7;font-family:Arial,Helvetica,sans-serif;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="background:#f4f5f7;padding:32px 16px;">'
        '<tr><td align="center">'
        '<table role="presentation" cellpadding="0" cellspacing="0" '
        'style="max-width:560px;width:100%;background:#ffffff;border-radius:8px;'
        'box-shadow:0 1px 3px rgba(0,0,0,0.12);">'
        f'<tr><td style="padding:28px 32px;">'
        f'<p style="margin:0 0 16px;font-size:12px;letter-spacing:1px;'
        f'color:#6b7280;text-transform:uppercase;">{escape(_BRAND)}</p>'
        f'<h1 style="margin:0 0 16px;font-size:22px;color:#111827;">'
        f"{escape(heading)}</h1>"
        f'{body_html}'
        f'<p style="margin:32px 0 0;font-size:12px;color:#9ca3af;">'
        "If you did not request this email, you can safely ignore it."
        "</p>"
        "</td></tr></table></td></tr></table></body></html>"
    )


def render_verification_email(
    *, full_name: str, link: str, expires_minutes: int
) -> EmailContent:
    """Render the email-verification message.

    Args:
        full_name: Recipient display name.
        link: Signed verification URL the recipient clicks.
        expires_minutes: Link validity window, echoed to the recipient.

    Returns:
        The subject, plain-text body, and HTML body.
    """
    subject = "Verify your email address"
    text = (
        f"Hi {full_name},\n\n"
        "Verify your email address to activate your SMU AI Assistant account:\n\n"
        f"{link}\n\n"
        f"The link expires in {expires_minutes} minutes.\n"
    )
    html = _layout(
        title=subject,
        heading="Verify your email address",
        body_html=(
            f"<p style='margin:0 0 16px;font-size:14px;color:#374151;'>"
            f"Hi {escape(full_name)},</p>"
            "<p style='margin:0 0 16px;font-size:14px;color:#374151;'>"
            "Click the button below to activate your SMU AI Assistant "
            "account:</p>"
            + _action_link_html("Verify email address", link)
            + f"<p style='margin:0;font-size:13px;color:#6b7280;'>"
            f"This link expires in {expires_minutes} minutes.</p>"
        ),
    )
    return EmailContent(subject=subject, text=text, html=html)


def render_password_reset_email(
    *, full_name: str, link: str, expires_minutes: int
) -> EmailContent:
    """Render the password-reset message.

    Args:
        full_name: Recipient display name.
        link: Signed reset URL the recipient clicks.
        expires_minutes: Link validity window, echoed to the recipient.

    Returns:
        The subject, plain-text body, and HTML body.
    """
    subject = "Reset your password"
    text = (
        f"Hi {full_name},\n\n"
        "We received a request to reset your SMU AI Assistant password. "
        "If this was you, open the link below to choose a new password:\n\n"
        f"{link}\n\n"
        f"The link expires in {expires_minutes} minutes and can only be used "
        "once.\n"
    )
    html = _layout(
        title=subject,
        heading="Reset your password",
        body_html=(
            f"<p style='margin:0 0 16px;font-size:14px;color:#374151;'>"
            f"Hi {escape(full_name)},</p>"
            "<p style='margin:0 0 16px;font-size:14px;color:#374151;'>"
            "We received a request to reset your SMU AI Assistant password. "
            "If this was you, click the button below:</p>"
            + _action_link_html("Reset password", link)
            + "<p style='margin:0;font-size:13px;color:#6b7280;'>"
            f"This link expires in {expires_minutes} minutes and can only be "
            "used once.</p>"
        ),
    )
    return EmailContent(subject=subject, text=text, html=html)


__all__ = ["EmailContent", "render_password_reset_email", "render_verification_email"]
