import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from sate_factlog.log import FactLog
from sate_treasury.cost_allocation import submit_pro_rata_shared_cost
from sate_treasury.ledger import blank

from sate_adequacy.champion_runner import run_champion_from_files
from sate_adequacy.export_dashboard import write_performance_dashboard
from sate_adequacy.report import build_adequacy_report
from sate_adequacy.runner import load_evidence, staging_evidence
from sate_adequacy.scenario_runner import run_scenario_suite


class OpenPhase22Tests(unittest.TestCase):
    def test_scenario_suite_has_executable_ts_am_oc_bf(self) -> None:
        result = run_scenario_suite()
        self.assertTrue(result.green)
        export = result.export()
        self.assertGreaterEqual(int(export["executable"]), 12)
        self.assertEqual(int(export["stub"]), 0)

    def test_champion_runner_and_dashboard_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            champion = {
                "rank_corr_vs_baseline": 0.2,
                "signals_ingested": 10,
                "mean_shadow_c": 0.25,
            }
            challenger = {
                "rank_corr_vs_baseline": 0.35,
                "signals_ingested": 10,
                "mean_shadow_c": 0.22,
            }
            c_path = root / "c.json"
            ch_path = root / "ch.json"
            c_path.write_text(json.dumps(champion), encoding="utf-8")
            ch_path.write_text(json.dumps(challenger), encoding="utf-8")
            verdict = run_champion_from_files(champion_path=c_path, challenger_path=ch_path)
            self.assertEqual(verdict.winner, "challenger")
            evidence = staging_evidence()
            report = build_adequacy_report(evidence, champion=verdict)
            self.assertIn("champion_challenger", report)
            write_performance_dashboard(evidence, destination=root)
            self.assertTrue((root / "performance-dashboard.json").is_file())

    def test_pro_rata_submit_helper(self) -> None:
        log = FactLog(sqlite3.connect(":memory:"), writers=frozenset({"treasury"}))
        state = submit_pro_rata_shared_cost(
            log,
            blank(),
            cost_id="shared-1",
            amount="30",
            currency="USD",
            vendor="host",
            evidence="inv",
            path="owner_paid",
            rcb_a="300",
            rcb_b="700",
            event_id="e-1",
            occurred_at="2026-10-23T00:00:00Z",
            recorded_at="2026-10-23T00:00:01Z",
            correlation_id="c-1",
        )
        self.assertEqual(len(state.allocations), 1)

    def test_load_evidence_staging_default(self) -> None:
        self.assertGreater(load_evidence().trade_count, 0)


if __name__ == "__main__":
    unittest.main()
