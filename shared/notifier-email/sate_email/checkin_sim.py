"""SIM-side lapse effects for OPS drills (**OP-01**–**OP-06**, mirrors kernel thresholds)."""

from __future__ import annotations

_EFFECTS = frozenset({"ok", "reminder", "manage_only", "flatten", "continue"})


def lapse_effect(
    *,
    days_without: int,
    account_mode: str,
    reminder_days: int = 7,
    manage_only_days: int = 10,
    flatten_days: int = 14,
) -> str:
    if account_mode == "SIM":
        return "continue"
    if days_without >= flatten_days:
        return "flatten"
    if days_without >= manage_only_days:
        return "manage_only"
    if days_without >= reminder_days:
        return "reminder"
    return "ok"


def assert_effect(op_id: str, expected: str, **kwargs: object) -> None:
    effect = lapse_effect(**kwargs)  # type: ignore[arg-type]
    if effect != expected:
        raise AssertionError(f"{op_id} expected {expected}, got {effect}")
    if effect not in _EFFECTS:
        raise AssertionError(f"unknown effect {effect}")
