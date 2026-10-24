import unittest

from sate_control.preflight import preflight_arm_live

from sate_live_readiness.staging import complete_assessment, incomplete_assessment


class PreflightLiveReadinessWireTests(unittest.TestCase):
    def test_live_readiness_reasons_merge(self) -> None:
        result = preflight_arm_live(
            scope="A",
            clean_recon=True,
            constitution_pinned=True,
            mode="SIM",
            live_readiness=incomplete_assessment(),
        )
        self.assertFalse(result.passed)
        self.assertTrue(any("capital_rcb" in item for item in result.reasons))

    def test_complete_live_readiness_passes_base(self) -> None:
        result = preflight_arm_live(
            scope="A",
            clean_recon=True,
            constitution_pinned=True,
            mode="SIM",
            live_readiness=complete_assessment(),
        )
        self.assertTrue(result.passed)


if __name__ == "__main__":
    unittest.main()
