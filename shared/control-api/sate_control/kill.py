"""Kill command validation (**A-KIL-04**, reduce-only asymmetry **A-KIL-02**)."""

from __future__ import annotations

from sate_control.scope import require_scope

_KILL_LEVELS = frozenset({"K1", "K2", "K3"})
_REDUCE_CHANNELS = frozenset({"telegram", "web", "cli", "trusted_contact"})
_RESUME_CHANNELS = frozenset({"web"})


def validate_kill(*, scope: str, kill_level: str, channel: str) -> dict[str, str]:
    if scope == "ALL":
        _require_all(scope)
    else:
        require_scope(scope)
    if kill_level not in _KILL_LEVELS:
        raise ValueError(f"kill level must be K1, K2, or K3, got {kill_level!r}")
    if channel not in _REDUCE_CHANNELS:
        raise ValueError("kill channel is not authorised")
    return {"scope": scope, "kill_level": kill_level, "channel": channel}


def validate_resume(channel: str) -> None:
    if channel not in _RESUME_CHANNELS:
        raise ValueError("resume requires the web control plane with passkey")


def _require_all(scope: str) -> str:
    if scope != "ALL":
        raise ValueError(f"explicit group scope required, got {scope!r}")
    return scope
