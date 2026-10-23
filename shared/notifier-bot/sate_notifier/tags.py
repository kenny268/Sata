"""Scope tags (**A-TG-01**). Mode is omitted until the desk actually has one."""

from __future__ import annotations

COMBINED_LABEL = (
    "Combined reporting — not transferable and not used for sizing or eligibility"
)


def scope_tag(scope: str, mode: str = "") -> str:
    if scope == "ALL":
        return "[ALL]"
    label = _mode_label(mode)
    if not label:
        return f"[{scope}]"
    return f"[{scope}-{label}]"


def halt_line(halt_command: str, *, partial_halt: bool) -> str:
    """Partial ALL halts must never render HALT_CONFIRMED_ALL (**TG-T-08**)."""
    command = halt_command.strip()
    if not command:
        return ""
    if partial_halt and command == "HALT_CONFIRMED_ALL":
        return "Halt: partial"
    if partial_halt and "HALT_CONFIRMED_ALL" in command:
        return "Halt: partial"
    return f"Halt: {command}"


def _mode_label(mode: str) -> str:
    upper = mode.strip().upper()
    if upper.startswith("LIVE"):
        return "LIVE"
    if upper == "SIM":
        return "SIM"
    return ""
