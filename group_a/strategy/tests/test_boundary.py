import unittest

from sate_strategy_a import stub_intent


class StrategyBoundaryTests(unittest.TestCase):
    def test_intent_is_group_a_and_not_sent(self) -> None:
        intent = stub_intent(intent_id="i-1", instrument="EURUSD")
        self.assertEqual(intent["group"], "A")
        self.assertNotIn("credentials", intent)


if __name__ == "__main__":
    unittest.main()
