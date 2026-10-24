"""SLO budgets for observability dashboards (**Phase 19**)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SloBudget:
    name: str
    target: float
    unit: str


KERNEL_STALL_SECONDS = SloBudget(name="kernel_heartbeat_stall", target=60.0, unit="seconds")
BRIDGE_LATENCY_MS = SloBudget(name="mt5_poll_latency_p99", target=500.0, unit="milliseconds")


def slo_snapshot(*, kernel_stall_sec: float, bridge_latency_ms: float) -> dict[str, object]:
    return {
        "kernel_stall_ok": kernel_stall_sec <= KERNEL_STALL_SECONDS.target,
        "kernel_stall_sec": kernel_stall_sec,
        "bridge_latency_ok": bridge_latency_ms <= BRIDGE_LATENCY_MS.target,
        "bridge_latency_ms": bridge_latency_ms,
    }
