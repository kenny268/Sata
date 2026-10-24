"""Mode badges for web and Telegram (**A-MOD-04**)."""

from __future__ import annotations

_BADGES = {
    "SIM": ("blue", "A-SIM"),
    "LIVE-L1": ("red", "A-LIVE"),
    "LIVE-L2": ("red", "A-LIVE"),
    "LIVE-L3": ("red", "A-LIVE"),
    "MANAGE_ONLY": ("amber", "A-MANAGE"),
    "HALTED": ("red", "A-HALTED"),
}


def badge(mode: str) -> tuple[str, str]:
    try:
        return _BADGES[mode]
    except KeyError as exc:
        raise ValueError(f"unknown mode {mode!r}") from exc
