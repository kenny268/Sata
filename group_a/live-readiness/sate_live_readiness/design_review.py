"""§17.1 design review checklist at LIVE gate."""

from __future__ import annotations

import os

DESIGN_REVIEW_ITEMS = (
    "pre_mortem",
    "red_team_release",
    "ablation_budget",
    "cost_audit",
    "complexity_budget",
    "appendix_d_register",
    "two_system_consistency",
    "state_audit",
)


def design_review_complete(*, env_override: bool | None = None) -> bool:
    if env_override is not None:
        return env_override
    return os.environ.get("SATE_DESIGN_REVIEW_COMPLETE", "").lower() in {"1", "true", "yes"}


def design_review_reasons(*, env_override: bool | None = None) -> list[str]:
    if design_review_complete(env_override=env_override):
        return []
    return ["s17_design_review_incomplete"]
