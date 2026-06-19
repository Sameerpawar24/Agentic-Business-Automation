import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from langchain_core.tools import tool
from src.core.config import settings

logger = logging.getLogger("agentic.email_tool")


def _send_smtp(to: str, subject: str, body: str) -> bool:
    """Internal helper that sends via SMTP. Returns True on success."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASS)
        server.sendmail(settings.SMTP_FROM, [to], msg.as_string())
    return True


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """
    Send an email to a recipient.
    If SMTP credentials are not configured, operates in dry-run mode and logs the email instead.
    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.
    Returns:
        Confirmation string indicating real send or dry-run.
    """
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        # Dry-run mode — log what would have been sent
        logger.info("[DRY-RUN EMAIL] To: %s | Subject: %s | Body: %s", to, subject, body)
        return (
            f"[DRY-RUN] Email NOT sent (no SMTP configured). "
            f"Would have sent to '{to}' with subject '{subject}'."
        )

    try:
        _send_smtp(to, subject, body)
        logger.info("Email sent to %s | Subject: %s", to, subject)
        return f"Email successfully sent to '{to}' with subject '{subject}'."
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to, str(exc))
        return f"Error sending email to '{to}': {str(exc)}"
