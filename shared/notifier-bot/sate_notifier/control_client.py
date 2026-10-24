"""control-api integration for reduce-only commands (**TG-PO-09**)."""

from __future__ import annotations

from sate_control.kill import validate_kill


def submit_kill(*, scope: str, kill_level: str) -> dict[str, str]:
    return validate_kill(scope=scope, kill_level=kill_level, channel="telegram")


def submit_mode_sim(*, scope: str) -> dict[str, str]:
    if scope != "A":
        raise ValueError("mode sim via telegram is Group A scoped")
    return {"scope": scope, "mode": "SIM", "channel": "telegram"}
