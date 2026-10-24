"""Black–Litterman blend **A-SIG-03–04**."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BlendResult:
    view: float
    advisory_used: bool
    signal_ref: str


def blend_views(
    *,
    kalman_direction: int,
    advisory_view: float | None,
    regime_tilt: bool,
) -> BlendResult:
    base = float(kalman_direction)
    if advisory_view is None:
        return BlendResult(view=base, advisory_used=False, signal_ref="kalman-only")
    if not regime_tilt:
        return BlendResult(view=base, advisory_used=False, signal_ref="kalman-regime-blocked")
    combined = (0.7 * base) + (0.3 * advisory_view)
    if combined > 0.1:
        view = 1.0
    elif combined < -0.1:
        view = -1.0
    else:
        view = 0.0
    return BlendResult(view=view, advisory_used=True, signal_ref="bl-kalman-advisory")
