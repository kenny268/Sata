"""Compose smoke: seeded 6-month harness + phase 23 gate report."""

from __future__ import annotations

import sqlite3

from sate_factlog.log import FactLog

from sate_adequacy.phase23_gate import build_phase23_report
from sate_adequacy.sim_clock import SimPeriod
from sate_adequacy.sim_period_harness import seed_six_month_evidence


def main() -> None:
    log = FactLog(
        sqlite3.connect(":memory:"),
        writers=frozenset({"sim-ops-a", "strategy-a"}),
        readers=frozenset({"sim-ops-a"}),
    )
    start = "2026-04-23T00:00:00Z"
    as_of = "2026-10-23T21:00:00Z"
    seed_six_month_evidence(log, period_start=start, as_of=as_of)
    period = SimPeriod(started_at=start, as_of=as_of)
    report = build_phase23_report(log, as_of=as_of, period=period)
    if not report["sim_period"]["calendar_gate_met"]:
        raise SystemExit("calendar gate not met in harness")
    if not report["ops_drills"]["gate_met"]:
        raise SystemExit("drill gate not met")
    print("phase23 ok", report["phase23_exit_met"])


if __name__ == "__main__":
    main()
