"""GET /state snapshot for the SPA."""

from __future__ import annotations

from sate_control.mode_badge import badge
from sate_control.reporting import tag_reporting_only


def group_state(
    *,
    scope: str,
    mode: str,
    halt_level: str,
    kill_state: str,
    heartbeat_ok: bool,
    fingerprint: str,
) -> dict[str, object]:
    color, tag = badge(mode)
    payload: dict[str, object] = {
        "scope": scope,
        "mode": mode,
        "halt_level": halt_level,
        "kill_state": kill_state,
        "heartbeat_ok": heartbeat_ok,
        "fingerprint": fingerprint,
        "mode_badge": {"color": color, "tag": tag},
    }
    return payload


def combined_reporting_state(*, a_equity: str, b_equity: str) -> dict[str, object]:
    return tag_reporting_only(
        {
            "scope": "ALL",
            "a_equity": a_equity,
            "b_equity": b_equity,
            "combined_equity_display": a_equity,
        }
    )
