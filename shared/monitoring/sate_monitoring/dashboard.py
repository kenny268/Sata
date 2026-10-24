"""In-process SLO dashboard snapshot (export to external UI at deploy time)."""

from __future__ import annotations

from dataclasses import dataclass

from sate_monitoring.slo import slo_snapshot


@dataclass(frozen=True)
class DashboardPanel:
    title: str
    ok: bool
    detail: str


def build_panels(*, kernel_stall_sec: float, bridge_latency_ms: float) -> list[DashboardPanel]:
    snap = slo_snapshot(kernel_stall_sec=kernel_stall_sec, bridge_latency_ms=bridge_latency_ms)
    return [
        DashboardPanel(
            title="Kernel heartbeat",
            ok=bool(snap["kernel_stall_ok"]),
            detail=f"{kernel_stall_sec:.0f}s stall budget 60s",
        ),
        DashboardPanel(
            title="MT5 poll latency",
            ok=bool(snap["bridge_latency_ok"]),
            detail=f"{bridge_latency_ms:.0f}ms p99 budget 500ms",
        ),
    ]
