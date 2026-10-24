"""Activate LIVE-L1 after web confirm (**§4.3**, **AM-A1**)."""

from __future__ import annotations

from sate_factlog.log import FactLog

from sate_live_l1.persist import persist_mode_transition, persist_ramp_started, persist_safe_window
from sate_live_l1.ramp import RAMP_FACTOR_L1_START, initial_ramp
from sate_live_l1.safe_window import SafeWindow
from sate_live_l1.shadow_twin import start_shadow_twin


def activate_live_l1(log: FactLog, *, at: str, first_session_id: str | None = None) -> dict[str, object]:
    window = SafeWindow(scheduled_at=at)
    if not window.ready():
        raise ValueError("safe_window_not_ready")
    persist_safe_window(log, scheduled_at=at)
    persist_mode_transition(log, from_mode="SIM", to_mode="LIVE-L1", at=at)
    ramp = initial_ramp(started_at=at)
    persist_ramp_started(log, ramp_factor=ramp.factor, started_at=at)
    twin_id = None
    if first_session_id:
        twin_id = start_shadow_twin(log, live_session_id=first_session_id, at=at)
    return {
        "mode": "LIVE-L1",
        "ramp_factor": RAMP_FACTOR_L1_START,
        "ramp_started_at": at,
        "shadow_twin_session_id": twin_id,
        "safe_window": "scheduled",
    }
