"""Appendix D email providers: console (CI) and SMTP (production)."""

from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Protocol


class EmailProvider(Protocol):
    def send(self, *, to: str, subject: str, body: str) -> None: ...


@dataclass
class ConsoleProvider:
    sent: list[dict[str, str]] = field(default_factory=list)

    def send(self, *, to: str, subject: str, body: str) -> None:
        self.sent.append({"to": to, "subject": subject, "body": body})


@dataclass(frozen=True)
class SmtpConfig:
    host: str
    port: int
    username: str
    password: str
    mail_from: str
    use_tls: bool = True
    timeout_sec: int = 30


@dataclass
class SmtpProvider:
    config: SmtpConfig

    @classmethod
    def from_env(cls) -> SmtpProvider:
        host = os.environ.get("SATE_SMTP_HOST", "").strip()
        port_text = os.environ.get("SATE_SMTP_PORT", "587").strip()
        user = os.environ.get("SATE_SMTP_USER", "").strip()
        password = os.environ.get("SATE_SMTP_PASSWORD", "")
        mail_from = os.environ.get("SATE_SMTP_FROM", user).strip()
        use_tls = os.environ.get("SATE_SMTP_TLS", "1").strip() not in {"0", "false", "False"}
        if not host or not user or not password or not mail_from:
            raise ValueError("SMTP requires SATE_SMTP_HOST, SATE_SMTP_USER, SATE_SMTP_PASSWORD, SATE_SMTP_FROM")
        port = int(port_text)
        if port < 1 or port > 65535:
            raise ValueError("SATE_SMTP_PORT must be a valid TCP port")
        return cls(
            SmtpConfig(
                host=host,
                port=port,
                username=user,
                password=password,
                mail_from=mail_from,
                use_tls=use_tls,
            )
        )

    def send(self, *, to: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["To"] = to
        message["From"] = self.config.mail_from
        message.set_content(body)
        with smtplib.SMTP(self.config.host, self.config.port, timeout=self.config.timeout_sec) as client:
            if self.config.use_tls:
                client.starttls()
            client.login(self.config.username, self.config.password)
            client.send_message(message)


def load_provider_from_env() -> EmailProvider:
    transport = os.environ.get("SATE_EMAIL_TRANSPORT", "console").strip().lower()
    if transport == "console":
        return ConsoleProvider()
    if transport == "smtp":
        return SmtpProvider.from_env()
    raise ValueError("SATE_EMAIL_TRANSPORT must be console or smtp")
