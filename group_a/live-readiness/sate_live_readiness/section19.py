"""§19 Definition of Done rows → explicit preflight reason codes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Section19Input:
    architecture_ok: bool
    code_ok: bool
    security_ok: bool
    testing_ok: bool
    broker_ok: bool
    operations_ok: bool


def section19_reasons(state: Section19Input) -> list[str]:
    reasons: list[str] = []
    if not state.architecture_ok:
        reasons.append("s19_architecture_incomplete")
    if not state.code_ok:
        reasons.append("s19_code_incomplete")
    if not state.security_ok:
        reasons.append("s19_security_incomplete")
    if not state.testing_ok:
        reasons.append("s19_testing_incomplete")
    if not state.broker_ok:
        reasons.append("s19_broker_incomplete")
    if not state.operations_ok:
        reasons.append("s19_operations_incomplete")
    return reasons
