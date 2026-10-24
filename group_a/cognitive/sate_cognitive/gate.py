"""Trading gate: advisory multiplier **0** until **CG-LIVE** (**A-COG-04**)."""

from __future__ import annotations

CG_LIVE_THRESHOLD_DEFINED = False


def trading_advisory_multiplier(*, account_mode: str) -> float:
    """LIVE-capable path keeps advisory contribution at zero in Phase 21."""
    _ = account_mode
    return 0.0
