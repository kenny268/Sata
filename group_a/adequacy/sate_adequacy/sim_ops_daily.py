"""Daily SIM ops rollup + optional drills."""

from __future__ import annotations

import os
import sqlite3

from sate_factlog.log import FactLog

from sate_adequacy.evidence_ledger import WRITER_ID, days_from_log, persist_day, rollup_from_log
from sate_adequacy.ops_drills import drills_from_log, persist_drill, run_all_drills
from sate_adequacy.sim_ops_wire import sim_ops_writers


def _log() -> FactLog:
    path = os.environ.get("SATE_SIM_OPS_FACTLOG", os.environ.get("SATE_STRATEGY_DB", ":memory:"))
    conn = sqlite3.connect(path) if path != ":memory:" else sqlite3.connect(":memory:")
    return FactLog(
        conn,
        writers=sim_ops_writers(),
        readers=frozenset({WRITER_ID, "strategy-a"}),
    )


def flush_day_summary(*, at: str) -> dict[str, object]:
    log = _log()
    roll = rollup_from_log(log, reader_id=WRITER_ID, as_of=at)
    day = at[:10]
    for record in days_from_log(log, reader_id=WRITER_ID, as_of=at):
        if record.day == day:
            persist_day(log, record, at=at)
            break
    if os.environ.get("SATE_PHASE23_RUN_DRILLS", "").lower() in {"1", "true", "yes"}:
        existing = drills_from_log(log, reader_id=WRITER_ID, as_of=at)
        if not existing.gate_met:
            for result in run_all_drills().results:
                persist_drill(log, result, at=at)
    return {
        "day": day,
        "ledger_days": roll.days,
        "reconciliation_clean_rate": roll.reconciliation_clean_rate,
        "trade_count": roll.trade_count,
    }


def main() -> None:
    at = os.environ.get("SATE_SIM_OPS_AT", os.environ.get("SATE_STRATEGY_NOW", "2026-10-23T21:00:00Z"))
    summary = flush_day_summary(at=at)
    print("sim ops daily ok", summary["day"])


if __name__ == "__main__":
    main()
