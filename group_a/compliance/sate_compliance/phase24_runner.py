"""Phase 24 broker verification runner."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from sate_factlog.log import FactLog

from sate_compliance.phase24_gate import build_phase24_report
from sate_compliance.phase24_log import persist_phase24_report


def _log() -> FactLog:
    path = os.environ.get("SATE_COMPLIANCE_FACTLOG", ":memory:")
    conn = sqlite3.connect(path) if path != ":memory:" else sqlite3.connect(":memory:")
    return FactLog(
        conn,
        writers=frozenset({"compliance-a", "control-api"}),
        readers=frozenset({"compliance-a", "control-api"}),
    )


def main() -> None:
    as_of = os.environ.get("SATE_COMPLIANCE_AT", "2026-10-23T21:00:00Z")
    log = _log()
    report = build_phase24_report(log, as_of=as_of)
    persist_phase24_report(log, event_id=f"phase24-{as_of}", report=report, at=as_of)
    out = Path(os.environ.get("SATE_PHASE24_REPORT_DIR", "/tmp/sate-phase24"))
    out.mkdir(parents=True, exist_ok=True)
    path = out / "phase24-report.json"
    path.write_text(json.dumps(report, sort_keys=True, indent=2), encoding="utf-8")
    print("phase24 report ok", "exit" if report["live_arm_allowed"] else "blocked")


if __name__ == "__main__":
    main()
