"""Phase 16 check-in validation."""

from __future__ import annotations

import unittest

from sate_control.checkin import validate_away, validate_checkin
from sate_control.trusted_contact import trusted_contact_notification


class CheckinValidationTests(unittest.TestCase):
    def test_web_passkey_is_strong_and_telegram_alive_is_weak(self) -> None:
        strong = validate_checkin(channel="web_passkey", passkey_assertion="assertion-1")
        self.assertEqual(strong["strength"], "strong")
        weak = validate_checkin(channel="telegram_alive")
        self.assertEqual(weak["strength"], "weak")

    def test_away_requires_passkey_and_respects_max(self) -> None:
        away = validate_away(channel="web_passkey", days=14)
        self.assertEqual(away["away_days"], "14")
        with self.assertRaises(ValueError):
            validate_away(channel="telegram_alive", days=3)
        with self.assertRaises(ValueError):
            validate_away(channel="web_passkey", days=31)

    def test_trusted_contact_is_informational_only(self) -> None:
        note = trusted_contact_notification(message="owner unreachable")
        self.assertTrue(note["informational"])
        with self.assertRaises(ValueError):
            trusted_contact_notification(message="x", action="arm_live")


if __name__ == "__main__":
    unittest.main()
