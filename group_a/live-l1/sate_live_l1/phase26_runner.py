"""Phase 26 staging session runner."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from sate_factlog.log import FactLog
from sate_mt5_bridge.bridge import Bridge
from sate_mt5_bridge.terminal import MockTerminal

from sate_live_l1.live_session import run_first_live_session
from sate_live_l1.phase26_gate import build_phase26_report
from sate_live_l1.transition import activate_live_l1


def _log() -> FactLog:
    path = os.environ.get("SATE_LIVE_L1_FACTLOG", ":memory:")
    conn = sqlite3.connect(path) if path != ":memory:" else sqlite3.connect(":memory:")
    return FactLog(
        conn,
        writers=frozenset({"live-l1-a", "sim-ops-a", "strategy-a", "kernel-a", "control-api"}),
        readers=frozenset({"live-l1-a", "sim-ops-a", "control-api"}),
    )


def main() -> None:
    at = os.environ.get("SATE_LIVE_L1_AT", "2026-10-23T22:00:00Z")
    log = _log()
    session_id = f"live-l1-{at[:10]}"
    activate_live_l1(log, at=at, first_session_id=session_id)
    terminal = MockTerminal(
        login="10001",
        server="Exness-MT5Trial",
        mode="SIM",
        bid="1.0850",
        ask="1.0852",
        server_time=at,
        settlement="demo",
        min_lot="1.25",
        lot_step="0.01",
        stops_level="0",
    )
    bridge = Bridge(terminal)
    bridge.connect("10001", "Exness-MT5Trial", {"group": "A", "injected": True}, instrument="EURUSD")
    result = run_first_live_session(bridge=bridge, log=log, at=at, session_id=session_id)
    bridge.close()
    report = build_phase26_report(log, as_of=at)
    out = Path(os.environ.get("SATE_PHASE26_REPORT_DIR", "/tmp/sate-phase26"))
    out.mkdir(parents=True, exist_ok=True)
    path = out / "phase26-report.json"
    payload = {"session": result, **report}
    path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")
    print("phase26 ok", "exit" if report["phase26_exit_met"] else "pending")


if __name__ == "__main__":
    main()
