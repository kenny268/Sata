import unittest

from sate_live_readiness.decisions import a_dec_04_reasons, a_dec_09_reasons
from sate_live_readiness.preflight_engine import LivePreflightInputs, assess_live_readiness
from sate_live_readiness.staging import complete_assessment, incomplete_assessment
from sate_live_readiness.verification_matrix import matrix_evidence_present


class LiveReadinessTests(unittest.TestCase):
    def test_matrix_evidence_present(self) -> None:
        self.assertTrue(matrix_evidence_present())

    def test_incomplete_blocks(self) -> None:
        reasons = incomplete_assessment().block_reasons()
        self.assertIn("capital_rcb_below_reference_floor", reasons)
        self.assertIn("a_dec_09_rpo_rto_unset", reasons)

    def test_complete_staging_passes(self) -> None:
        self.assertFalse(complete_assessment().block_reasons())

    def test_a_dec_04_lock_hours(self) -> None:
        doc = {"meta": {"tighten_lock_hours": 0, "loosen_lock_hours": 0}}
        self.assertIn("a_dec_04_time_lock_open", a_dec_04_reasons(doc))

    def test_a_dec_09_default_blocked(self) -> None:
        self.assertIn("a_dec_09_rpo_rto_unset", a_dec_09_reasons())

    def test_broker_section19(self) -> None:
        assessment = assess_live_readiness(
            LivePreflightInputs(
                as_of="2026-10-23T21:00:00Z",
                broker_preflight_ok=False,
                rpo_rto_resolved=True,
                constitution={
                    "meta": {"tighten_lock_hours": 24, "loosen_lock_hours": 72},
                    "risk": {"broker_balance_cap": "1"},
                    "mode": {"state": "SIM"},
                },
            )
        )
        self.assertIn("s19_broker_incomplete", assessment.block_reasons())


if __name__ == "__main__":
    unittest.main()
