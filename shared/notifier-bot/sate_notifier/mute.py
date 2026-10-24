""" /mute command (**TG-PO-13**, TG-T-06)."""

from __future__ import annotations

import re

from sate_notifier.delivery import DeliveryPolicy

_MUTE = re.compile(r"^/mute(?:@\w+)?(?:\s+(?P<dur>\d+)(?P<unit>[hm]))?$", re.IGNORECASE)


def parse_mute(text: str) -> int | None:
    match = _MUTE.match(text.strip())
    if not match:
        return None
    if not match.group("dur"):
        return 3600
    amount = int(match.group("dur"))
    unit = (match.group("unit") or "h").lower()
    return amount * 3600 if unit == "h" else amount * 60


def apply_mute(policy: DeliveryPolicy, text: str, *, now: float) -> dict[str, str]:
    seconds = parse_mute(text)
    if seconds is None:
        raise ValueError("usage: /mute or /mute 30m or /mute 2h")
    policy.mute(duration_sec=seconds, now=now)
    return {"muted_sec": str(seconds), "note": "CRITICAL alerts are never muted"}
