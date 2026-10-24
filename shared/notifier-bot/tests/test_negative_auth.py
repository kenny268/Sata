"""TG-T-07 negative auth: bot cannot increase exposure."""

from __future__ import annotations

import sqlite3
import unittest

from sate_control.kill import validate_resume
from sate_factlog.log import FactLog

from sate_notifier.allowlist import Allowlist
from sate_notifier.bot import NotifierBot
from sate_notifier.commands import classify_command, parse_command
from sate_notifier.control_client import submit_kill


class NegativeAuthTests(unittest.TestCase):
    def test_forbidden_commands_point_to_web(self) -> None:
        for cmd in ("/resume", "/live", "/loosen"):
            decision = classify_command(parse_command(cmd))
            self.assertEqual(decision["class"], "abstain")

    def test_telegram_cannot_validate_resume(self) -> None:
        with self.assertRaises(ValueError):
            validate_resume("telegram")

    def test_intruder_is_discarded(self) -> None:
        log = FactLog(sqlite3.connect(":memory:"), writers=frozenset({"notifier-bot"}))
        bot = NotifierBot(log=log, allowlist=Allowlist(chat_id="100", user_id="owner"))
        result = bot.handle_update(
            update_id=1,
            chat_id="999",
            user_id="other",
            text="/kill",
            message_id="1",
        )
        self.assertEqual(result["reason"], "auth.failed")

    def test_kill_validation_stays_reduce_only_channel(self) -> None:
        payload = submit_kill(scope="A", kill_level="K1")
        self.assertEqual(payload["channel"], "telegram")


if __name__ == "__main__":
    unittest.main()
