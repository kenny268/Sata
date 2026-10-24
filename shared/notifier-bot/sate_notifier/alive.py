"""`/alive` records presence without privilege (**A-CHK-01**)."""

from __future__ import annotations


def handle_alive(*, chat_allowed: bool, user_allowed: bool) -> dict[str, str]:
    if not chat_allowed or not user_allowed:
        raise PermissionError("telegram allowlist required for /alive")
    return {
        "channel": "telegram_alive",
        "strength": "weak",
        "effect": "reset_checkin_timer",
        "risk_increasing": "false",
    }
