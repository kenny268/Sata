import sqlite3
import unittest

from sate_factlog.log import FactLog
from sate_strategy_a.sim_runner import run_continuous_session

from sate_adequacy.evidence_ledger import rollup_from_log
from sate_adequacy.phase23_gate import build_phase23_report
from sate_adequacy.sim_clock import SimPeriod
from sate_adequacy.sim_ops_wire import record_sim_session, sim_ops_writers


class SimOpsWireTests(unittest.TestCase):
    def test_runner_records_period_and_sessions(self) -> None:
        import os

        os.environ["SATE_SIM_OPS_FACTLOG"] = ":memory:"
        os.environ["SATE_SIM_PERIOD_START"] = "2026-04-23T00:00:00Z"
        at = "2026-05-01T10:00:00Z"
        result = run_continuous_session(at=at)
        self.assertTrue(result["journal_logged"])
        log = FactLog(
            sqlite3.connect(":memory:"),
            writers=sim_ops_writers(),
            readers=frozenset(sim_ops_writers()),
        )
        record_sim_session(
            log,
            session_id="manual-1",
            journal_logged=True,
            order_placed=True,
            verdict="Allow",
            at="2026-05-01T11:00:00Z",
        )
        roll = rollup_from_log(log, reader_id="sim-ops-a", as_of="2026-05-01T12:00:00Z")
        self.assertGreaterEqual(roll.trade_count, 1)

    def test_phase23_from_runner_sessions(self) -> None:
        log = FactLog(
            sqlite3.connect(":memory:"),
            writers=sim_ops_writers(),
            readers=frozenset({"sim-ops-a"}),
        )
        start = "2026-04-23T00:00:00Z"
        for index in range(30):
            record_sim_session(
                log,
                session_id=f"s-{index}",
                journal_logged=True,
                order_placed=index % 2 == 0,
                verdict="Allow" if index % 2 == 0 else "Abstain",
                at=f"2026-05-{index + 1:02d}T12:00:00Z",
            )
        from sate_adequacy.evidence_ledger import persist_period_start

        persist_period_start(log, started_at=start, recorded_at=start)
        as_of = "2026-10-23T21:00:00Z"
        report = build_phase23_report(log, as_of=as_of, period=SimPeriod(started_at=start, as_of=as_of))
        self.assertGreater(report["ledger_rollup"]["days"], 0)


if __name__ == "__main__":
    unittest.main()
