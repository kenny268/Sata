import unittest

from sate_live_l1.arming_delay import arming_delay_elapsed
from sate_live_l1.c4_runbook import C4_STEPS
from sate_live_l1.ramp import RAMP_FACTOR_L1_START, initial_ramp


class LiveL1Tests(unittest.TestCase):
    def test_c4_steps(self) -> None:
        self.assertIn("telegram_otp_web_confirm", C4_STEPS)

    def test_ramp_start(self) -> None:
        ramp = initial_ramp(started_at="2026-10-23T00:00:00Z")
        self.assertEqual(ramp.factor, RAMP_FACTOR_L1_START)

    def test_arming_delay(self) -> None:
        self.assertFalse(
            arming_delay_elapsed(
                started_at="2026-10-23T00:00:00Z",
                as_of="2026-10-23T12:00:00Z",
            )
        )


if __name__ == "__main__":
    unittest.main()
