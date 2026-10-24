import json
import unittest

from sate_adequacy.criteria import A_DEC_03_OPEN
from sate_adequacy.evidence import SimAdequacyEvidence
from sate_adequacy.report import build_adequacy_report
from sate_adequacy.runner import staging_evidence


class AdequacyReportTests(unittest.TestCase):
    def test_reproducible_digest(self) -> None:
        evidence = staging_evidence()
        first = build_adequacy_report(evidence)
        second = build_adequacy_report(evidence)
        self.assertEqual(first["report_digest"], second["report_digest"])

    def test_sim04_blocked_on_dec_03(self) -> None:
        self.assertTrue(A_DEC_03_OPEN)
        report = build_adequacy_report(staging_evidence())
        sim04 = next(item for item in report["criteria"] if item["id"] == "A-SIM-04")
        self.assertEqual(sim04["status"], "blocked")
        self.assertIn("A-DEC-03", report["blockers"])

    def test_json_round_trip(self) -> None:
        evidence = SimAdequacyEvidence(
            generated_at="2026-10-23T21:00:00Z",
            sim_months_continuous=3.0,
            reconciliation_clean_rate=0.90,
            net_sharpe_after_costs=0.5,
            monthly_returns_net=(0.01, 0.02, 0.01),
            trade_count=50,
            bootstrap_excess_lower_bound=None,
            l2_plus_unresolved_last_60d=1,
            parameter_changes_last_3_months=1,
            untradeable_session_rate=0.6,
            strategy_version_frozen="x",
        )
        report = build_adequacy_report(evidence)
        self.assertFalse(report["overall_pass"])
        json.dumps(report)


if __name__ == "__main__":
    unittest.main()
