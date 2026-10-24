"""Owner check-in and away mode (**A-CHK-01**, **A-CHK-02**)."""

from __future__ import annotations

_STRONG = frozenset({"web_passkey"})
_WEAK = frozenset({"telegram_alive"})


def validate_checkin(*, channel: str, passkey_assertion: str | None = None) -> dict[str, str]:
    if channel in _STRONG:
        if not passkey_assertion:
            raise ValueError("check-in on the web requires a passkey assertion")
        return {"channel": channel, "strength": "strong"}
    if channel in _WEAK:
        return {"channel": channel, "strength": "weak", "reduce_only_scope": "true"}
    raise ValueError("check-in channel is not authorised")


def validate_away(*, channel: str, days: int, max_away_days: int = 30) -> dict[str, str]:
    if channel not in _STRONG:
        raise ValueError("away mode requires the web control plane with passkey")
    if days < 1 or days > max_away_days:
        raise ValueError(f"away days must be between 1 and {max_away_days}")
    return {"channel": channel, "away_days": str(days)}
