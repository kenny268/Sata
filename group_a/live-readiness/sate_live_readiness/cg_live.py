"""**CG-LIVE** / **A-COG-04** initial LIVE path (advisory zero)."""

from __future__ import annotations

import os

from sate_cognitive.gate import CG_LIVE_THRESHOLD_DEFINED, trading_advisory_multiplier

from sate_live_readiness.decisions import load_cg_live_record


def cg_live_reasons(*, confirmed: bool | None = None) -> list[str]:
    if confirmed is True:
        return []
    record = load_cg_live_record()
    if CG_LIVE_THRESHOLD_DEFINED:
        return ["cg_live_threshold_not_implemented"]
    if trading_advisory_multiplier(account_mode="LIVE") != 0.0:
        return ["cg_live_advisory_nonzero"]
    if os.environ.get("SATE_CG_LIVE_INITIAL_ADVISORY_ZERO", "").lower() in {"1", "true", "yes"}:
        return []
    if record.get("initial_live_path") == "advisory_zero":
        return ["cg_live_initial_path_unconfirmed"]
    return ["cg_live_criteria_unconfirmed"]
