"""Fact-log event → Telegram template (**TG-PO-03**)."""

from __future__ import annotations

_SEVERITY = {
    "halt": "WARN",
    "kill": "CRITICAL",
    "reconciliation": "CRITICAL",
    "check_in": "NOTICE",
    "owner_action": "INFO",
}


def classify_event(event_type: str) -> dict[str, str]:
    severity = _SEVERITY.get(event_type, "INFO")
    category = event_type.upper().replace("_", "-")[:16]
    return {"category": category, "severity": severity}
