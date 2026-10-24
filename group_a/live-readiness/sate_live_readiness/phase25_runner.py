"""Phase 25 verification suite runner."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from sate_factlog.log import FactLog

from sate_live_readiness.persist import persist_phase25_report
from sate_live_readiness.phase25_gate import build_phase25_report


def _log() -> FactLog:
    path = os.environ.get("SATE_LIVE_READINESS_FACTLOG", ":memory:")
    conn = sqlite3.connect(path) if path != ":memory:" else sqlite3.connect(":memory:")
    return FactLog(
        conn,
        writers=frozenset({"live-readiness-a", "compliance-a", "sim-ops-a"}),
        readers=frozenset({"live-readiness-a", "compliance-a", "sim-ops-a", "control-api"}),
    )


def main() -> None:
    as_of = os.environ.get("SATE_LIVE_READINESS_AT", "2026-10-23T21:00:00Z")
    log = _log()
    report = build_phase25_report(log, as_of=as_of)
    persist_phase25_report(log, event_id=f"phase25-{as_of}", report=report, at=as_of)
    out = Path(os.environ.get("SATE_PHASE25_REPORT_DIR", "/tmp/sate-phase25"))
    out.mkdir(parents=True, exist_ok=True)
    path = out / "phase25-report.json"
    path.write_text(json.dumps(report, sort_keys=True, indent=2), encoding="utf-8")
    print("phase25 report ok", "exit" if report["a_p1_06_preflight_ok"] else "blocked")


if __name__ == "__main__":
    main()
