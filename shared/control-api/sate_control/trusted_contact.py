"""Trusted contact notifications (**A-CHK-04**)."""

from __future__ import annotations

_RISK_ACTIONS = frozenset({"resume", "arm_live", "loosen_limits", "ratify_rcb"})


def trusted_contact_notification(*, message: str, action: str | None = None) -> dict[str, str | bool]:
    if action in _RISK_ACTIONS:
        raise ValueError("trusted contact cannot perform operator actions")
    return {"informational": True, "message": message, "kill_delegate_only": True}


def trusted_contact_lapse_notice(*, days_without: int, manage_only_days: int = 10) -> dict[str, str | bool]:
    if days_without < manage_only_days:
        raise ValueError("trusted contact lapse notices start at MANAGE_ONLY day")
    return trusted_contact_notification(
        message=f"Owner check-in lapse: {days_without} day(s) without strong web check-in.",
    )
