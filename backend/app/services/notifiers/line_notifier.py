import httpx

from app.services.notifiers.base import BaseNotifier

LINE_NOTIFY_URL = "https://notify-api.line.me/api/notify"


class LineNotifier(BaseNotifier):
    async def send(self, target: str, subject: str, body: str) -> None:
        """
        target: LINE Notify personal access token
        (each user gets their own token from https://notify-bot.line.me/my/)
        """
        message = f"\n【{subject}】\n{body}"

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                LINE_NOTIFY_URL,
                headers={"Authorization": f"Bearer {target}"},
                data={"message": message},
                timeout=10,
            )
            resp.raise_for_status()
