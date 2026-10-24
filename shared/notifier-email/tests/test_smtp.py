from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from sate_email.appendix_d import email_provider_assumption
from sate_email.provider import SmtpConfig, SmtpProvider, load_provider_from_env


class SmtpProviderTests(unittest.TestCase):
    def test_send_uses_tls_and_login(self) -> None:
        client = MagicMock()
        client.__enter__.return_value = client
        client.__exit__.return_value = False
        provider = SmtpProvider(
            SmtpConfig(
                host="smtp.example.com",
                port=587,
                username="owner@example.com",
                password="secret",
                mail_from="owner@example.com",
            )
        )
        with patch("sate_email.provider.smtplib.SMTP", return_value=client) as factory:
            provider.send(to="trusted@example.com", subject="Reminder", body="Day 7")
        factory.assert_called_once_with("smtp.example.com", 587, timeout=30)
        client.starttls.assert_called_once()
        client.login.assert_called_once_with("owner@example.com", "secret")
        client.send_message.assert_called_once()

    def test_from_env_requires_host_user_and_password(self) -> None:
        env = {
            "SATE_SMTP_HOST": "smtp.mail.test",
            "SATE_SMTP_PORT": "465",
            "SATE_SMTP_USER": "a@b.c",
            "SATE_SMTP_PASSWORD": "pw",
            "SATE_SMTP_FROM": "a@b.c",
            "SATE_SMTP_TLS": "0",
        }
        with patch.dict(os.environ, env, clear=False):
            provider = SmtpProvider.from_env()
        self.assertEqual(provider.config.host, "smtp.mail.test")
        self.assertFalse(provider.config.use_tls)

    def test_load_provider_selects_smtp(self) -> None:
        env = {
            "SATE_EMAIL_TRANSPORT": "smtp",
            "SATE_SMTP_HOST": "smtp.mail.test",
            "SATE_SMTP_USER": "a@b.c",
            "SATE_SMTP_PASSWORD": "pw",
            "SATE_SMTP_FROM": "a@b.c",
        }
        with patch.dict(os.environ, env, clear=False):
            provider = load_provider_from_env()
        self.assertIsInstance(provider, SmtpProvider)

    def test_appendix_d_assumption_documents_smtp(self) -> None:
        row = email_provider_assumption(transport="smtp", verified_at="2026-10-23T00:00:00Z")
        self.assertEqual(row["assumption_id"], "APP-D-EMAIL-01")
        self.assertEqual(row["transport"], "smtp")


if __name__ == "__main__":
    unittest.main()
