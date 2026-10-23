import sqlite3
import unittest

from sate_factlog.log import FactLog

from sate_adequacy.ops_drills import run_all_drills
from sate_adequacy.phase23_gate import build_phase23_report
from sate_adequacy.sim_clock import SimPeriod
from sate_adequacy.sim_period_harness import seed_six_month_evidence


class Phase23Tests(unittest.TestCase):
    def test_harness_meets_calendar_and_drills(self) -> None:
        log = FactLog(
            sqlite3.connect(":memory:"),
            writers=frozenset({"sim-ops-a", "strategy-a"}),
            readers=frozenset({"sim-ops-a"}),
        )
        start = "2026-04-23T00:00:00Z"
        as_of = "2026-10-23T21:00:00Z"
        seed_six_month_evidence(log, period_start=start, as_of=as_of)
        period = SimPeriod(started_at=start, as_of=as_of)
        self.assertTrue(period.calendar_gate_met)
        report = build_phase23_report(log, as_of=as_of, period=period)
        self.assertTrue(report["ops_drills"]["gate_met"])
        self.assertTrue(report["phase23_exit_met"])

    def test_drill_suite_ids(self) -> None:
        suite = run_all_drills()
        self.assertTrue(suite.gate_met)
        by_id = {item.drill_id: item.steps for item in suite.results}
        self.assertIn("resume_after_clean", by_id["C.3"])
        self.assertIn("reentry_block_14d", by_id["AM-A5"])
        self.assertEqual(by_id["C.10"], ["watchdog_restart", "reconcile_before_resume"])
        self.assertEqual(by_id["C.6"], ["day7_presence", "day10_lift", "day14_recovery"])


if __name__ == "__main__":
    unittest.main()
