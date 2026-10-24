"""Abstention paths **A-PR-04**, **TS-03**."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AbstainDecision:
    reason: str
    digest: str
    category: str = "ABSTAIN"


def abstain(*, reason: str, detail: str) -> AbstainDecision:
    return AbstainDecision(reason=reason, digest=f"ABSTAIN {reason}: {detail[:160]}")
