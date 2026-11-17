"""Sending email.

Two interchangeable senders:

* ConsoleEmailSender (development): sends nothing. Each email is saved as a
  text file in backend/var/outbox/ so you can open it and click the link.
* SmtpEmailSender (production): sends through a real mail server.

Which one is used is chosen by the EMAIL_BACKEND setting.
"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import EmailMessage as MimeMessage
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    body: str


class EmailSender(Protocol):
    def send(self, email: Email) -> None: ...


class ConsoleEmailSender:
    """Writes each email to a file instead of sending it."""

    def __init__(self, outbox_dir: Path) -> None:
        self._outbox_dir = outbox_dir

    def send(self, email: Email) -> None:
        self._outbox_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
        safe_to = "".join(ch if ch.isalnum() or ch in "@.-_" else "_" for ch in email.to)
        path = self._outbox_dir / f"{stamp}-{safe_to}.txt"
        path.write_text(
            f"To: {email.to}\nSubject: {email.subject}\n\n{email.body}\n", encoding="utf-8"
        )
        # The log names the file but never prints the body: it holds a
        # secret link, and logs are read more widely than this folder.
        logger.info("Development email saved to %s", path)


class SmtpEmailSender:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send(self, email: Email) -> None:
        settings = self._settings
        message = MimeMessage()
        message["From"] = settings.email_from
        message["To"] = email.to
        message["Subject"] = email.subject
        message.set_content(email.body)

        if settings.smtp_host is None:  # Guarded by Settings; kept for the type checker.
            raise RuntimeError("SMTP_HOST is not configured.")
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.starttls()  # Refuse to send credentials or mail unencrypted.
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password.get_secret_value())
            server.send_message(message)


@lru_cache
def get_email_sender() -> EmailSender:
    settings = get_settings()
    if settings.email_backend == "smtp":
        return SmtpEmailSender(settings)
    return ConsoleEmailSender(settings.email_outbox_dir)


def send_safely(sender: EmailSender, email: Email) -> None:
    """Send, and log (rather than crash) if the mail server fails.

    Emails go out after the response has been returned, so there is nobody
    left to show an error to. The failure must still be recorded.
    """
    try:
        sender.send(email)
    except Exception:
        logger.exception("Could not send email with subject %r", email.subject)


# --- The emails Roomie sends -------------------------------------------


def verification_email(to: str, token: str, settings: Settings) -> Email:
    link = f"{settings.frontend_url}/verify-email?token={token}"
    return Email(
        to=to,
        subject="Confirm your email for Roomie",
        body=(
            "Welcome to Roomie.\n\n"
            "Please confirm your email address by opening this link:\n"
            f"{link}\n\n"
            f"The link works for {settings.email_verification_hours} hours and can be used once.\n"
            "If you did not create a Roomie account, you can ignore this email."
        ),
    )


def password_reset_email(to: str, token: str, settings: Settings) -> Email:
    link = f"{settings.frontend_url}/reset-password?token={token}"
    return Email(
        to=to,
        subject="Reset your Roomie password",
        body=(
            "Someone asked to reset the password for this Roomie account.\n\n"
            "To choose a new password, open this link:\n"
            f"{link}\n\n"
            f"The link works for {settings.password_reset_minutes} minutes and can be used once.\n"
            "If this was not you, ignore this email. Your password has not changed."
        ),
    )
