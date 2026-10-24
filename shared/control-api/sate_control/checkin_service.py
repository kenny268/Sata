"""Apply validated check-in / away commands toward the kernel book (**A-CHK-01**–**A-CHK-02**)."""

from __future__ import annotations

from sate_control.checkin import validate_away, validate_checkin


def apply_checkin(*, channel: str, passkey_assertion: str | None = None) -> dict[str, str]:
    validated = validate_checkin(channel=channel, passkey_assertion=passkey_assertion)
    return {
        **validated,
        "kernel_action": "record_checkin",
        "effect": "reset_last_checkin_day",
    }


def apply_away(*, channel: str, passkey_assertion: str | None, days: int, max_away_days: int = 30) -> dict[str, str]:
    if channel == "web_passkey" and not passkey_assertion:
        raise ValueError("away mode requires a passkey assertion")
    validated = validate_away(channel=channel, days=days, max_away_days=max_away_days)
    return {
        **validated,
        "kernel_action": "set_checkin_away",
        "effect": "extend_away_until_day",
    }
