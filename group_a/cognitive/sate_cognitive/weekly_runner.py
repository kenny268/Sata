"""Weekly SIM shadow report (**Phase 21** exit)."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from sate_factlog.log import FactLog

from sate_cognitive.shadow import ShadowAccumulator, ShadowReport
from sate_cognitive.shadow_log import persist_weekly_shadow
from sate_cognitive.shadow_store import load_accumulator


def write_weekly_report(report: ShadowReport, *, destination: Path | None = None) -> Path:
    target = destination or Path(os.environ.get("SATE_SHADOW_REPORT_DIR", "/tmp/sate-shadow"))
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"shadow-{report.week}.json"
    path.write_text(json.dumps(report.export(), sort_keys=True, indent=2), encoding="utf-8")
    return path


def run_weekly_stub(*, week: str) -> ShadowReport:
    acc = ShadowAccumulator(week=week)
    acc.record_ingest(ok=True, signal_id="stub-1", shadow_q=0.1, shadow_c=0.2)
    acc.record_ingest(ok=True, signal_id="stub-2", shadow_q=-0.05, shadow_c=0.25)
    acc.attach_outcome("stub-1", 1.0)
    acc.attach_outcome("stub-2", -1.0)
    report = acc.weekly_report()
    write_weekly_report(report)
    return report


def run_weekly_from_state(*, week: str, state_file: Path) -> ShadowReport:
    acc = load_accumulator(state_file)
    if acc.week != week:
        acc.week = week
    report = acc.weekly_report()
    write_weekly_report(report)
    log_path = os.environ.get("SATE_SHADOW_FACTLOG_PATH")
    if log_path:
        log = FactLog(
            sqlite3.connect(log_path),
            writers=frozenset({"cognitive-a"}),
            readers=frozenset({"cognitive-a", "strategy-a"}),
        )
        at = os.environ.get("SATE_SHADOW_AT", "2026-10-23T21:00:00Z")
        persist_weekly_shadow(log, event_id=f"shadow-weekly-{week}", report=report, at=at)
    return report


def main() -> None:
    week = os.environ.get("SATE_SHADOW_WEEK", "2026-W43")
    state = os.environ.get("SATE_SHADOW_STATE_FILE")
    if state and Path(state).is_file():
        run_weekly_from_state(week=week, state_file=Path(state))
    else:
        run_weekly_stub(week=week)
    print("cognitive weekly shadow ok")


if __name__ == "__main__":
    main()
