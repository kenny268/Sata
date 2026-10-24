"""LIVE arming preflight (**AM-02**, **AM-03**)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sate_control.scope import require_scope

try:
    from sate_compliance.gate import BrokerLiveGate
except ImportError:  # pragma: no cover - optional until Phase 24 on PYTHONPATH
    BrokerLiveGate = None  # type: ignore[misc, assignment]


@dataclass
class PreflightResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)


def preflight_arm_live(
    *,
    scope: str,
    clean_recon: bool,
    constitution_pinned: bool,
    mode: str,
    arming_cancelled: bool = False,
    broker_gate: object | None = None,
    live_readiness: object | None = None,
) -> PreflightResult:
    require_scope(scope)
    reasons: list[str] = []
    if arming_cancelled:
        reasons.append("arming_cancelled")
    if mode != "SIM":
        reasons.append("mode_not_sim")
    if not clean_recon:
        reasons.append("recon_not_clean")
    if not constitution_pinned:
        reasons.append("constitution_unpinned")
    if broker_gate is not None and BrokerLiveGate is not None:
        reasons.extend(broker_gate.block_reasons())  # type: ignore[union-attr]
    if live_readiness is not None:
        reasons.extend(live_readiness.block_reasons())  # type: ignore[union-attr]
    return PreflightResult(passed=not reasons, reasons=reasons)
