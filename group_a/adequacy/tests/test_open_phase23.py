import sqlite3
import unittest

from sate_factlog.log import FactLog

from sate_adequacy.evidence_ledger import load_days_from_log, rollup
from sate_adequacy.phase23_gate import build_phase23_report
from sate_adequacy.sim_clock import SIM_MONTHS_REQUIRED, SimPeriod
from sate_adequacy.sim_period_harness import seed_six_month_evidence


class OpenPhase23Tests(unittest.TestCase):
    def test_a_sim_02_trajectory_from_ledger(self) -> None:
        log = FactLog(
            sqlite3.connect(":memory:"),
            writers=frozenset({"sim-ops-a", "strategy-a"}),
            readers=frozenset({"sim-ops-a"}),
        )
        start = "2026-04-23T00:00:00Z"
        as_of = "2026-10-23T21:00:00Z"
        seed_six_month_evidence(log, period_start=start, as_of=as_of, days=120)
        roll = rollup(load_days_from_log(log, reader_id="sim-ops-a", as_of=as_of))
        self.assertGreaterEqual(roll.reconciliation_clean_rate, 0.95)
        report = build_phase23_report(log, as_of=as_of, period=SimPeriod(started_at=start, as_of=as_of))
        sim02 = next(c for c in report["adequacy_report"]["criteria"] if c["id"] == "A-SIM-02")
        self.assertEqual(sim02["status"], "pass")
        self.assertGreaterEqual(
            float(report["sim_period"]["months_elapsed"]),
            SIM_MONTHS_REQUIRED,
        )
        self.assertFalse(report["operator_wall_clock_elapsed"])
        self.assertIn("ledger_rollup", report)

    def test_wall_clock_requires_operator_flag(self) -> None:
        import os

        log = FactLog(
            sqlite3.connect(":memory:"),
            writers=frozenset({"sim-ops-a", "strategy-a"}),
            readers=frozenset({"sim-ops-a"}),
        )
        start = "2026-04-23T00:00:00Z"
        as_of = "2026-10-23T21:00:00Z"
        seed_six_month_evidence(log, period_start=start, as_of=as_of, days=184)
        os.environ["SATE_SIM_WALL_CLOCK_ELAPSED"] = "true"
        report = build_phase23_report(log, as_of=as_of, period=SimPeriod(started_at=start, as_of=as_of))
        self.assertTrue(report["operator_wall_clock_elapsed"])
        os.environ.pop("SATE_SIM_WALL_CLOCK_ELAPSED", None)


if __name__ == "__main__":
    unittest.main()
