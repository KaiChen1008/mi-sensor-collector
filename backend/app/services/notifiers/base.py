from abc import ABC, abstractmethod


class BaseNotifier(ABC):
    @abstractmethod
    async def send(self, target: str, subject: str, body: str) -> None:
        """Send a notification.

        Args:
            target: channel-specific destination (email address, chat_id, etc.)
            subject: short title
            body: full message text
        """
