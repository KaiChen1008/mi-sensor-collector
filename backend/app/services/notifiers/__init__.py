from app.services.notifiers.base import BaseNotifier
from app.services.notifiers.email_notifier import EmailNotifier
from app.services.notifiers.line_notifier import LineNotifier
from app.services.notifiers.telegram_notifier import TelegramNotifier

NOTIFIERS: dict[str, BaseNotifier] = {
    "email": EmailNotifier(),
    "telegram": TelegramNotifier(),
    "line": LineNotifier(),
}

__all__ = ["NOTIFIERS", "BaseNotifier"]
