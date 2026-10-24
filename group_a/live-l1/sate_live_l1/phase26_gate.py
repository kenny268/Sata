"""Phase 26 exit report."""

from __future__ import annotations

from sate_factlog.log import FactLog

from sate_live_l1.c4_runbook import runbook_export


def build_phase26_report(log: FactLog | None, *, as_of: str) -> dict[str, object]:
    live_session = False
    recon = False
    shadow = False
    ramp = False
    if log is not None:
        rows = _replay(log, as_of=as_of)
        for row in rows:
            kind = row.payload.get("kind")
            if kind == "mode_transition" and row.payload.get("to_mode") == "LIVE-L1":
                live_session = True
            if kind == "live_post_session_recon" and row.payload.get("stops_verified_on_broker"):
                recon = True
            if kind == "shadow_twin_started":
                shadow = True
            if kind == "ramp_clock_started":
                ramp = True
    return {
        "phase": 26,
        "as_of": as_of,
        "c4_runbook": runbook_export(),
        "live_l1_activated": live_session,
        "shadow_twin_started": shadow,
        "ramp_clock_started": ramp,
        "first_session_recon_stops_verified": recon,
        "phase26_exit_met": live_session and shadow and ramp and recon,
    }


def _replay(log: FactLog, *, as_of: str) -> list:
    for reader in ("live-l1-a", "control-api", "sim-ops-a"):
        try:
            return log.replay_through(group_scope="A", as_of=as_of, reader_id=reader)
        except PermissionError:
            continue
    return []
