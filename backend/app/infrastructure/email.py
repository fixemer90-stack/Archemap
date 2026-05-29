"""Email provider abstraction and implementations."""

from __future__ import annotations

import smtplib
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog

from app.config import settings

logger = structlog.get_logger()


class EmailProvider(ABC):
    @abstractmethod
    async def send(self, to: str, subject: str, html_body: str, text_body: str = "") -> None:
        """Send an email."""


class ConsoleEmailProvider(EmailProvider):
    """Logs emails to stdout. For development."""

    async def send(self, to: str, subject: str, html_body: str, text_body: str = "") -> None:
        logger.info(
            "email_sent_console",
            to=to,
            subject=subject,
            body_preview=text_body[:200] if text_body else html_body[:200],
        )


class SmtpEmailProvider(EmailProvider):
    """Sends emails via SMTP. For production."""

    async def send(self, to: str, subject: str, html_body: str, text_body: str = "") -> None:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to
        msg["Subject"] = subject

        if text_body:
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            if settings.SMTP_USE_TLS:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
                server.ehlo()
                server.starttls()
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)

            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

            server.sendmail(settings.SMTP_FROM_EMAIL, to, msg.as_string())
            server.quit()

            logger.info("email_sent_smtp", to=to, subject=subject)
        except Exception:
            logger.exception("email_send_failed", to=to, subject=subject)
            raise


def get_email_provider() -> EmailProvider:
    """Factory: returns the configured email provider."""
    if settings.EMAIL_PROVIDER == "smtp":
        return SmtpEmailProvider()
    return ConsoleEmailProvider()
