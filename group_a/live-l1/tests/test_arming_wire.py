import os
import unittest

from sate_control.arming import ArmingSession
from sate_control.preflight import PreflightResult

_PASSKEY = "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGWFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHk"


class ArmingDelayTests(unittest.TestCase):
    def test_confirm_blocks_before_delay(self) -> None:
        os.environ.pop("SATE_ARMING_DELAY_HOURS", None)
        session = ArmingSession(scope="A")
        session.start_arm(
            passkey_assertion=_PASSKEY,
            preflight=PreflightResult(passed=True),
            started_at="2026-10-23T00:00:00Z",
            otp="999999",
        )
        with self.assertRaises(ValueError) as ctx:
            session.confirm(
                code="999999",
                passkey_assertion=_PASSKEY,
                now="2026-10-23T12:00:00Z",
            )
        self.assertEqual(str(ctx.exception), "arming_delay_not_elapsed")

    def test_skip_delay_allows_confirm(self) -> None:
        session = ArmingSession(scope="A")
        session.start_arm(
            passkey_assertion=_PASSKEY,
            preflight=PreflightResult(passed=True),
            started_at="2026-10-23T00:00:00Z",
            otp="999999",
        )
        live = session.confirm(
            code="999999",
            passkey_assertion=_PASSKEY,
            now="2026-10-23T01:00:00Z",
            skip_delay=True,
        )
        self.assertEqual(live["mode"], "LIVE-L1")


if __name__ == "__main__":
    unittest.main()
