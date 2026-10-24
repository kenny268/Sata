"""Kernel heartbeat and stall detection (**C.2**, exit ≤60s)."""

from __future__ import annotations

from dataclasses import dataclass

from sate_monitoring.alerts import AlertRouter, CriticalAlert


@dataclass
class KernelStall:
    detected: bool
    elapsed_sec: float
    alert_fired: bool


class HeartbeatMonitor:
    def __init__(self, *, stall_threshold_sec: float = 30.0, alert_budget_sec: float = 60.0) -> None:
        self._threshold = stall_threshold_sec
        self._budget = alert_budget_sec
        self._last_beat: float | None = None

    def beat(self, *, now: float) -> None:
        self._last_beat = now

    def evaluate(self, *, now: float, router: AlertRouter) -> KernelStall:
        if self._last_beat is None:
            return KernelStall(detected=False, elapsed_sec=0.0, alert_fired=False)
        elapsed = now - self._last_beat
        if elapsed <= self._threshold:
            return KernelStall(detected=False, elapsed_sec=elapsed, alert_fired=False)
        fired = False
        if elapsed <= self._budget:
            fired = router.route(
                CriticalAlert(
                    group_scope="A",
                    code="kernel_heartbeat_lost",
                    message=f"KERNEL-A heartbeat stale {elapsed:.0f}s",
                )
            )
        return KernelStall(detected=True, elapsed_sec=elapsed, alert_fired=fired)
