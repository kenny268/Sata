"""TG-PO-11–15 and TG-PO-08 coverage."""

from __future__ import annotations

import sqlite3
import unittest

from sate_factlog.log import FactLog

from sate_notifier.allowlist import Allowlist
from sate_notifier.bot import NotifierBot
from sate_notifier.delivery import DeliveryPolicy
from sate_notifier.fact_lookup import explain_why
from sate_notifier.mute import apply_mute
from sate_notifier.templates import format_outbound
from sate_notifier.templates_health import error_notice


class P1CommandTests(unittest.TestCase):
    def test_why_is_fact_sourced(self) -> None:
        log = FactLog(sqlite3.connect(":memory:"), writers=frozenset({"notifier-bot"}))
        log.append(
            event_id="v-8f3a",
            event_type="verdict",
            group_scope="A",
            occurred_at="2026-10-23T00:00:00Z",
            recorded_at="2026-10-23T00:00:00Z",
            correlation_id="v-8f3a",
            writer_id="notifier-bot",
            payload={"intent_id": "i-1"},
        )
        why = explain_why(log, "8f3a")
        self.assertIn("v-8f3a", why["fact_ref"])
        self.assertIn("Fact ref", why["text"])

    def test_mute_and_critical_bypass(self) -> None:
        policy = DeliveryPolicy()
        apply_mute(policy, "/mute 1h", now=100.0)
        self.assertFalse(policy.should_deliver("INFO", now=100.0))
        self.assertTrue(policy.should_deliver("CRITICAL", now=100.0))

    def test_away_and_digest_and_templates(self) -> None:
        log = FactLog(sqlite3.connect(":memory:"), writers=frozenset({"notifier-bot"}))
        bot = NotifierBot(log=log, allowlist=Allowlist(chat_id="1", user_id="owner"))
        away = bot.handle_update(
            update_id=1,
            chat_id="1",
            user_id="owner",
            text="/away",
            message_id="m-away",
        )
        self.assertEqual(away["status"], "abstain")
        self.assertIn("web_url", away)
        digest = bot.handle_update(
            update_id=2,
            chat_id="1",
            user_id="owner",
            text="/digest",
            message_id="m-dig",
        )
        self.assertIn("text", digest)
        health = bot.handle_update(
            update_id=3,
            chat_id="1",
            user_id="owner",
            text="/health",
            message_id="m-h",
        )
        self.assertIn("HEALTH", health["text"])
        treasury = bot.handle_update(
            update_id=4,
            chat_id="1",
            user_id="owner",
            text="/treasury",
            message_id="m-t",
        )
        self.assertIn("TREASURY", treasury["text"])

    def test_templates_reject_secrets(self) -> None:
        with self.assertRaises(ValueError):
            format_outbound("leaked bot_token=abc")
        critical = error_notice(scope="A", code="fact_log", detail="write failed")
        self.assertEqual(critical["severity"], "CRITICAL")


if __name__ == "__main__":
    unittest.main()
