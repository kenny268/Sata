"""GET /state snapshot for the SPA."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from sate_control.mode_badge import badge
from sate_control.reporting import tag_reporting_only


_CAPITAL_FIELDS = (
    "equity",
    "realised_pnl",
    "settled",
    "reserved",
    "withdrawable",
    "ratified_base",
    "pending_obligations",
)


def unknown_capital() -> dict[str, str]:
    return {key: "unknown" for key in _CAPITAL_FIELDS}


def group_state(
    *,
    scope: str,
    mode: str,
    halt_level: str,
    kill_state: str,
    heartbeat_ok: bool,
    fingerprint: str,
    capital: dict[str, str],
    attention: list[str],
    trading_revoked: bool,
    partial_halt: bool,
    halt_command: str,
    exposure: str,
    margin: str,
    distance_to_limits: str,
    arming_phase: str,
    arming_reasons: list[str],
    constitution_loaded: bool,
    active_version: object,
    pending_count: int,
    time_lock: str,
) -> dict[str, object]:
    color, tag = badge(mode)
    return {
        "scope": scope,
        "mode": mode,
        "halt_level": halt_level,
        "kill_state": kill_state,
        "heartbeat_ok": heartbeat_ok,
        "fingerprint": fingerprint,
        "mode_badge": {"color": color, "tag": tag},
        "capital": {key: capital.get(key, "unknown") for key in _CAPITAL_FIELDS},
        "attention": attention,
        "risk": {
            "exposure": exposure,
            "margin": margin,
            "distance_to_limits": distance_to_limits,
            "partial_halt": partial_halt,
            "trading_revoked": trading_revoked,
            "halt_command": halt_command,
        },
        "arming": {"phase": arming_phase, "reasons": arming_reasons},
        "constitution": {
            "loaded": constitution_loaded,
            "active_version": active_version,
            "pending_count": pending_count,
            "time_lock": time_lock,
        },
    }


def attention_flags(
    *,
    capital_loaded: bool,
    heartbeat_ok: bool,
    halt_level: str,
    kill_state: str,
    trading_revoked: bool,
    constitution_loaded: bool,
    session_expires_at: str,
    arming_phase: str,
) -> list[str]:
    flags: list[str] = []
    if not capital_loaded:
        flags.append("capital_unloaded")
    if not heartbeat_ok:
        flags.append("heartbeat_down")
    if halt_level:
        flags.append(f"halt_{halt_level}")
    if kill_state:
        flags.append(f"kill_{kill_state}")
    if trading_revoked:
        flags.append("trading_revoked")
    if not constitution_loaded:
        flags.append("constitution_unloaded")
    if not session_expires_at:
        flags.append("session_ttl_unset")
    if arming_phase == "blocked":
        flags.append("arming_blocked")
    return flags


def combined_reporting_state(*, a_equity: str, b_equity: str) -> dict[str, object]:
    return tag_reporting_only(
        {
            "scope": "ALL",
            "a_equity": a_equity,
            "b_equity": b_equity,
            "combined_equity_display": _display_sum(a_equity, b_equity),
        }
    )


def _display_sum(left: str, right: str) -> str:
    try:
        total = Decimal(left) + Decimal(right)
    except InvalidOperation:
        return "unknown"
    text = format(total, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
