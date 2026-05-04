from email.mime.text import MIMEText

import aiosmtplib

from app.config import settings
from app.services.notifiers.base import BaseNotifier


class EmailNotifier(BaseNotifier):
    async def send(self, target: str, subject: str, body: str) -> None:
        if not settings.smtp_user:
            raise RuntimeError("SMTP credentials not configured")

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from or settings.smtp_user
        msg["To"] = target

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
