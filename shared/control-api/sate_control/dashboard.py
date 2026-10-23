"""Scope-parameterised dashboard reads (§13.3). Figures stay unknown until a feed notes them."""

from __future__ import annotations

_POSITION_KEYS = ("instrument", "quantity", "stop", "pending", "fill_price", "slippage")
_PERF_FIELDS = ("net_of_cost", "attribution", "drawdown", "benchmark")
_PERF_MODES = ("SIM", "LIVE")


def blank_performance() -> dict[str, str]:
    return {key: "unknown" for key in _PERF_FIELDS}


def positions_view(*, scope: str, loaded: bool, rows: list[dict[str, str]]) -> dict[str, object]:
    return {"scope": scope, "loaded": loaded, "positions": rows}


def clean_position(row: dict[str, object]) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for key in _POSITION_KEYS:
        value = row.get(key, "")
        if not isinstance(value, str):
            raise ValueError(f"{key} must be a string")
        cleaned[key] = value
    return cleaned


def performance_view(*, scope: str, books: dict[str, dict[str, str]]) -> dict[str, object]:
    return {
        "scope": scope,
        "books": {mode: dict(books[mode]) for mode in _PERF_MODES},
        "books_stay_separate": True,
    }


def eligibility_view(
    *,
    scope: str,
    constitution_blockers: list[str],
    arming_reasons: list[str],
) -> dict[str, object]:
    reasons = [*constitution_blockers, *arming_reasons, "live_final_gate"]
    return {
        "scope": scope,
        "reason_codes": reasons,
        "final_live_gate": False,
    }


def journal_view(*, scope: str, entries: list[dict[str, object]]) -> dict[str, object]:
    return {"scope": scope, "entries": entries, "why_from_log_only": True}


def treasury_view(
    *,
    scope: str,
    cash_floor: str,
    reimbursement_owed: str,
    cases: list[object],
    withdrawals: list[object],
) -> dict[str, object]:
    return {
        "scope": scope,
        "cash_floor": cash_floor,
        "reimbursement_owed": reimbursement_owed,
        "cases": cases,
        "withdrawals": withdrawals,
        "read_only": True,
    }


def health_view(
    *,
    scope: str,
    heartbeat_ok: bool,
    broker: str,
    hash_chain: str,
    replay_events: int,
    notifications: list[str],
) -> dict[str, object]:
    return {
        "scope": scope,
        "process_heartbeat": heartbeat_ok,
        "broker": broker,
        "hash_chain": hash_chain,
        "replay_events": replay_events,
        "notifications": notifications,
    }
