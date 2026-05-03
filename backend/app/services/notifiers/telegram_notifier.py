import httpx

from app.config import settings
from app.services.notifiers.base import BaseNotifier


class TelegramNotifier(BaseNotifier):
    async def send(self, target: str, subject: str, body: str) -> None:
        if not settings.telegram_bot_token:
            raise RuntimeError("Telegram bot token not configured")

        text = f"*{subject}*\n\n{body}"
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                json={"chat_id": target, "text": text, "parse_mode": "Markdown"},
                timeout=10,
            )
            resp.raise_for_status()
