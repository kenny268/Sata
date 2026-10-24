from __future__ import annotations

import unittest

from sate_control.preflight import preflight_arm_live


class PreflightTests(unittest.TestCase):
    def test_am03_cancelled_arm_is_blocked(self) -> None:
        result = preflight_arm_live(
            scope="A",
            clean_recon=True,
            constitution_pinned=True,
            mode="SIM",
            arming_cancelled=True,
        )
        self.assertFalse(result.passed)
        self.assertIn("arming_cancelled", result.reasons)


if __name__ == "__main__":
    unittest.main()
