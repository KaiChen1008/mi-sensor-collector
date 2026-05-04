"""Unit tests for notification channel implementations."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestEmailNotifier:
    @pytest.mark.asyncio
    async def test_sends_email(self):
        with (
            patch("app.services.notifiers.email_notifier.settings") as mock_settings,
            patch(
                "app.services.notifiers.email_notifier.aiosmtplib.send", new_callable=AsyncMock
            ) as mock_send,
        ):
            mock_settings.smtp_user = "sender@example.com"
            mock_settings.smtp_from = "sender@example.com"
            mock_settings.smtp_host = "smtp.example.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_password = "secret"

            from app.services.notifiers.email_notifier import EmailNotifier

            notifier = EmailNotifier()
            await notifier.send("recipient@example.com", "Test Subject", "Test body")

            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args[1]
            assert call_kwargs["hostname"] == "smtp.example.com"
            assert call_kwargs["username"] == "sender@example.com"

    @pytest.mark.asyncio
    async def test_raises_when_not_configured(self):
        with patch("app.services.notifiers.email_notifier.settings") as mock_settings:
            mock_settings.smtp_user = ""

            from app.services.notifiers.email_notifier import EmailNotifier

            notifier = EmailNotifier()
            with pytest.raises(RuntimeError, match="SMTP credentials not configured"):
                await notifier.send("r@e.com", "s", "b")


class TestTelegramNotifier:
    @pytest.mark.asyncio
    async def test_posts_to_telegram_api(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("app.services.notifiers.telegram_notifier.settings") as mock_settings,
            patch(
                "app.services.notifiers.telegram_notifier.httpx.AsyncClient",
                return_value=mock_client,
            ),
        ):
            mock_settings.telegram_bot_token = "123:ABC"

            from app.services.notifiers.telegram_notifier import TelegramNotifier

            notifier = TelegramNotifier()
            await notifier.send("987654321", "Alert", "Body text")

            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert "sendMessage" in call_args[0][0]
            payload = call_args[1]["json"]
            assert payload["chat_id"] == "987654321"
            assert "Alert" in payload["text"]

    @pytest.mark.asyncio
    async def test_raises_when_no_token(self):
        with patch("app.services.notifiers.telegram_notifier.settings") as mock_settings:
            mock_settings.telegram_bot_token = ""

            from app.services.notifiers.telegram_notifier import TelegramNotifier

            notifier = TelegramNotifier()
            with pytest.raises(RuntimeError, match="Telegram bot token not configured"):
                await notifier.send("123", "s", "b")


class TestLineNotifier:
    @pytest.mark.asyncio
    async def test_posts_to_line_notify_api(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.services.notifiers.line_notifier.httpx.AsyncClient", return_value=mock_client
        ):
            from app.services.notifiers.line_notifier import LINE_NOTIFY_URL, LineNotifier

            notifier = LineNotifier()
            await notifier.send("my-line-token", "High Humidity", "Humidity is 80%")

            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == LINE_NOTIFY_URL
            assert "my-line-token" in call_args[1]["headers"]["Authorization"]
            assert "High Humidity" in call_args[1]["data"]["message"]


class TestNotifiersRegistry:
    def test_all_channels_registered(self):
        from app.services.notifiers import NOTIFIERS

        assert "email" in NOTIFIERS
        assert "telegram" in NOTIFIERS
        assert "line" in NOTIFIERS

    def test_all_implement_base(self):
        from app.services.notifiers import NOTIFIERS
        from app.services.notifiers.base import BaseNotifier

        for name, notifier in NOTIFIERS.items():
            assert isinstance(notifier, BaseNotifier), f"{name} is not a BaseNotifier"
