"""Phase 23 SIM ops evidence runner."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from sate_factlog.log import FactLog

from sate_adequacy.phase23_gate import build_phase23_report, resolve_period
from sate_adequacy.phase23_log import persist_phase23_report
from sate_adequacy.sim_ops_wire import ensure_period_started


def _log() -> FactLog:
    path = os.environ.get("SATE_SIM_OPS_FACTLOG", ":memory:")
    conn = sqlite3.connect(path) if path != ":memory:" else sqlite3.connect(":memory:")
    return FactLog(
        conn,
        writers=frozenset({"sim-ops-a", "strategy-a", "adequacy-a", "cognitive-a"}),
        readers=frozenset({"sim-ops-a", "adequacy-a"}),
    )


def main() -> None:
    as_of = os.environ.get("SATE_SIM_OPS_AT", "2026-10-23T21:00:00Z")
    log = _log()
    ensure_period_started(log, at=as_of)
    period = resolve_period(log, as_of=as_of, env_start=os.environ.get("SATE_SIM_PERIOD_START"))
    report = build_phase23_report(log, as_of=as_of, period=period)
    persist_phase23_report(log, event_id=f"phase23-{as_of}", report=report, at=as_of)
    out = Path(os.environ.get("SATE_PHASE23_REPORT_DIR", "/tmp/sate-phase23"))
    out.mkdir(parents=True, exist_ok=True)
    path = out / "phase23-report.json"
    path.write_text(json.dumps(report, sort_keys=True, indent=2), encoding="utf-8")
    print("phase23 report ok", "exit" if report["phase23_exit_met"] else "pending")


if __name__ == "__main__":
    main()
