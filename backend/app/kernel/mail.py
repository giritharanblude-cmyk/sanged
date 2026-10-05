import logging
import smtplib
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> bool:
    if not settings.smtp_host:
        if settings.is_local:
            # Local development has no real mailbox. Log the body so an OTP
            # login can still be completed from `docker compose logs api`.
            # Strictly gated on app_env=local so this can never leak in prod.
            logger.warning("SMTP not configured; logging email to %s instead: %s", to, body)
            return True
        logger.warning("SMTP not configured, skipping email to %s", to)
        return False
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from
        msg["To"] = to
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as s:
            if settings.smtp_starttls:
                s.starttls()
            if settings.smtp_user:
                s.login(settings.smtp_user, settings.smtp_password)
            s.sendmail(settings.smtp_from, [to], msg.as_string())
        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
        return False
