from __future__ import annotations

import unittest

from sate_notifier.reminder import maybe_send_reminder


class TelegramReminderTests(unittest.TestCase):
    def test_day7_sends_parallel_to_email(self) -> None:
        self.assertFalse(maybe_send_reminder(days_without=6)["sent"])
        payload = maybe_send_reminder(days_without=7)
        self.assertTrue(payload["sent"])
        self.assertEqual(payload["channel"], "telegram")


if __name__ == "__main__":
    unittest.main()
