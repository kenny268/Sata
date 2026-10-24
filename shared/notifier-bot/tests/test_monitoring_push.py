import unittest

from sate_notifier.delivery import DeliveryPolicy
from sate_notifier.monitoring_push import deliver_monitoring_payload


class MonitoringPushTests(unittest.TestCase):
    def test_critical_delivered_during_mute(self) -> None:
        policy = DeliveryPolicy()
        policy.mute(duration_sec=3600, now=100.0)
        payload = {
            "text": "[A-LIVE] HEALTH CRITICAL",
            "category": "HEALTH",
            "severity": "CRITICAL",
        }
        self.assertTrue(deliver_monitoring_payload(payload, policy, now=100.0))

    def test_notice_blocked_when_muted(self) -> None:
        policy = DeliveryPolicy()
        policy.mute(duration_sec=3600, now=100.0)
        payload = {"text": "warn", "category": "INFO", "severity": "NOTICE"}
        self.assertFalse(deliver_monitoring_payload(payload, policy, now=100.0))


if __name__ == "__main__":
    unittest.main()
