"""TG-T-06 CRITICAL bypasses mute."""

from __future__ import annotations

import unittest

from sate_notifier.delivery import DeliveryPolicy


class DeliveryTests(unittest.TestCase):
    def test_critical_delivered_while_muted(self) -> None:
        policy = DeliveryPolicy()
        policy.mute(duration_sec=3600, now=100.0)
        self.assertFalse(policy.should_deliver("INFO", now=100.0))
        self.assertTrue(policy.should_deliver("CRITICAL", now=100.0))


if __name__ == "__main__":
    unittest.main()
