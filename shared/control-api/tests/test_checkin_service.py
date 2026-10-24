from __future__ import annotations

import unittest

from sate_control.checkin_service import apply_away, apply_checkin
from sate_control.trusted_contact import trusted_contact_lapse_notice


class CheckinServiceTests(unittest.TestCase):
    def test_apply_checkin_maps_to_kernel_record(self) -> None:
        applied = apply_checkin(channel="telegram_alive")
        self.assertEqual(applied["kernel_action"], "record_checkin")

    def test_apply_away_maps_to_kernel_set_away(self) -> None:
        applied = apply_away(channel="web_passkey", passkey_assertion="assert-1", days=7)
        self.assertEqual(applied["kernel_action"], "set_checkin_away")

    def test_trusted_contact_lapse_is_informational_from_day10(self) -> None:
        note = trusted_contact_lapse_notice(days_without=10)
        self.assertTrue(note["informational"])


if __name__ == "__main__":
    unittest.main()
