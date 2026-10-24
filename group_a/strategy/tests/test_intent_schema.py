import unittest

from sate_strategy_a.intent import build_intent, validate_intent
from sate_strategy_a.universe import validate_instrument


class IntentSchemaTests(unittest.TestCase):
    def test_live_l1_eurusd_only(self) -> None:
        validate_instrument("EURUSD", account_mode="LIVE", rung="LIVE-L1")
        with self.assertRaises(ValueError):
            validate_instrument("XAUUSD", account_mode="LIVE", rung="LIVE-L1")

    def test_intent_schema(self) -> None:
        intent = build_intent(
            intent_id="i-1",
            account_mode="SIM",
            instrument="EURUSD",
            side="BUY",
            quantity="0.01",
            protective_stop="1.0700",
            strategy_id="test",
            created_at="2026-10-23T00:00:00Z",
        )
        validate_intent(intent)
        self.assertEqual(intent["group"], "A")


if __name__ == "__main__":
    unittest.main()
