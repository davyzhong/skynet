"""Report distribution channels."""

import smtplib
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import httpx

from app.config import get_settings


class BaseChannel(ABC):
    """Abstract base class for notification channels."""

    @abstractmethod
    async def send(self, content: str, **kwargs) -> bool:
        """Send content through the channel."""
        pass


class FeishuChannel(BaseChannel):
    """Feishu (Lark) webhook notification channel."""

    def __init__(self, webhook_url: str | None = None):
        settings = get_settings()
        self.webhook_url = webhook_url or settings.notification.feishu_webhook_url

    async def send(self, content: str, **kwargs) -> bool:
        """Send message to Feishu webhook."""
        if not self.webhook_url:
            return False

        payload = {
            "msg_type": "text",
            "content": {"text": content},
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=payload, timeout=10)
                return response.status_code == 200
        except Exception:
            return False


class EmailChannel(BaseChannel):
    """Email notification channel."""

    def __init__(
        self,
        smtp_host: str = "localhost",
        smtp_port: int = 587,
        smtp_user: str | None = None,
        smtp_password: str | None = None,
        from_addr: str | None = None,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_addr = from_addr or smtp_user

    async def send(
        self,
        content: str,
        to_addrs: list[str] | None = None,
        subject: str = "SkyNet Report",
        **kwargs
    ) -> bool:
        """Send email via SMTP."""
        if not to_addrs:
            return False

        msg = MIMEMultipart()
        msg["From"] = self.from_addr or "skynet@example.com"
        msg["To"] = ", ".join(to_addrs)
        msg["Subject"] = subject

        msg.attach(MIMEText(content, "html" if "<html" in content else "plain"))

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.ehlo()
                if self.smtp_port == 587:
                    server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            return True
        except Exception:
            return False


class WeChatWorkChannel(BaseChannel):
    """WeChat Work webhook notification channel."""

    def __init__(self, webhook_url: str | None = None):
        settings = get_settings()
        self.webhook_url = webhook_url or settings.notification.wechat_work_webhook_url

    async def send(self, content: str, **kwargs) -> bool:
        """Send message to WeChat Work webhook."""
        if not self.webhook_url:
            return False

        payload = {
            "msgtype": "text",
            "text": {"content": content},
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=payload, timeout=10)
                return response.status_code == 200
        except Exception:
            return False


class DingTalkChannel(BaseChannel):
    """DingTalk webhook notification channel."""

    def __init__(self, webhook_url: str | None = None):
        settings = get_settings()
        self.webhook_url = webhook_url or settings.notification.dingtalk_webhook_url

    async def send(self, content: str, **kwargs) -> bool:
        """Send message to DingTalk webhook."""
        if not self.webhook_url:
            return False

        payload = {
            "msgtype": "text",
            "text": {"content": content},
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=payload, timeout=10)
                return response.status_code == 200
        except Exception:
            return False


class DistributionManager:
    """Manages distribution of reports to multiple channels."""

    def __init__(self):
        self.channels: dict[str, BaseChannel] = {}

    def register_channel(self, name: str, channel: BaseChannel) -> None:
        """Register a notification channel."""
        self.channels[name] = channel

    def unregister_channel(self, name: str) -> bool:
        """Unregister a notification channel."""
        if name in self.channels:
            del self.channels[name]
            return True
        return False

    async def distribute(
        self,
        content: str,
        channels: list[str] | None = None,
        **kwargs
    ) -> dict[str, bool]:
        """
        Distribute content to specified channels.

        Args:
            content: Content to send
            channels: List of channel names to use (None = all)
            **kwargs: Additional arguments for channels

        Returns:
            Dictionary mapping channel name to success status
        """
        results = {}
        target_channels = channels if channels else list(self.channels.keys())

        for channel_name in target_channels:
            channel = self.channels.get(channel_name)
            if channel:
                try:
                    results[channel_name] = await channel.send(content, **kwargs)
                except Exception:
                    results[channel_name] = False
            else:
                results[channel_name] = False

        return results
