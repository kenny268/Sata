from __future__ import annotations

import unittest

from sate_email.provider import ConsoleProvider
from sate_email.reminder import ReminderScheduler


class ReminderTests(unittest.TestCase):
    def test_day7_sends_email_independent_of_telegram(self) -> None:
        provider = ConsoleProvider()
        scheduler = ReminderScheduler(provider, reminder_days=7)
        self.assertFalse(scheduler.maybe_send(to="owner@example.com", days_without=6))
        self.assertTrue(scheduler.maybe_send(to="owner@example.com", days_without=7))
        self.assertEqual(len(provider.sent), 1)


if __name__ == "__main__":
    unittest.main()
