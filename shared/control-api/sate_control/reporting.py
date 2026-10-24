"""Combined reporting label (**INV-03**)."""

from __future__ import annotations

COMBINED_REPORTING_LABEL = (
    "Combined reporting — not transferable and not used for sizing or eligibility"
)


def tag_reporting_only(payload: dict[str, object]) -> dict[str, object]:
    tagged = dict(payload)
    tagged["reporting_only"] = True
    tagged["label"] = COMBINED_REPORTING_LABEL
    return tagged


def reject_global_risk_scope(scope: str) -> None:
    if scope in {"GLOBAL", "A+B", "COMBINED"}:
        raise ValueError("risk-bearing operations cannot use a global scope")
