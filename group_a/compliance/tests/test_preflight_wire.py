import unittest

from sate_control.preflight import preflight_arm_live

from sate_compliance.staging import complete_gate, incomplete_gate


class PreflightBrokerWireTests(unittest.TestCase):
    def test_incomplete_broker_blocks_arm(self) -> None:
        result = preflight_arm_live(
            scope="A",
            clean_recon=True,
            constitution_pinned=True,
            mode="SIM",
            broker_gate=incomplete_gate(),
        )
        self.assertFalse(result.passed)
        self.assertTrue(any("inv08" in reason or "broker" in reason for reason in result.reasons))

    def test_complete_broker_passes_with_base_checks(self) -> None:
        result = preflight_arm_live(
            scope="A",
            clean_recon=True,
            constitution_pinned=True,
            mode="SIM",
            broker_gate=complete_gate(),
        )
        self.assertTrue(result.passed)


if __name__ == "__main__":
    unittest.main()
