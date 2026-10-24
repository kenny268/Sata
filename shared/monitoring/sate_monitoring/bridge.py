"""MT5 bridge observability (**§14.1** broker domain)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BridgeObservation:
    group_scope: str
    adapter_state: str
    poll_failures: int
    latency_ms: int


def observe_bridge(*, adapter_state: str, poll_failures: int, latency_ms: int) -> BridgeObservation:
    allowed = {"HEALTHY", "DEGRADED", "UNAVAILABLE", "UNVERIFIED", "DISCONNECTED", "RECONCILING"}
    if adapter_state not in allowed:
        raise ValueError(f"adapter_state must be one of {sorted(allowed)}")
    normalized = {
        "HEALTHY": "connected",
        "DEGRADED": "degraded",
        "UNAVAILABLE": "unavailable",
        "UNVERIFIED": "degraded",
        "DISCONNECTED": "unavailable",
        "RECONCILING": "degraded",
    }[adapter_state]
    return BridgeObservation(
        group_scope="A",
        adapter_state=normalized,
        poll_failures=poll_failures,
        latency_ms=latency_ms,
    )
