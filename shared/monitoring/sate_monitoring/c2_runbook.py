"""Runbook **C.2** kernel heartbeat lost."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class C2Runbook:
    steps: list[str] = field(default_factory=list)

    def step1_fail_closed(self) -> None:
        self.steps.append("fail_closed")

    def step2_restart_and_reload_halt(self, *, reloaded: bool) -> None:
        if not reloaded:
            raise ValueError("halt state must reload from disk")
        self.steps.append("restart_reload_halt")

    def step3_reconcile(self, *, clean: bool) -> None:
        if not clean:
            raise ValueError("reconciliation must be clean before resume")
        self.steps.append("reconcile")

    def step4_manual_portal_if_needed(self, *, used: bool) -> None:
        self.steps.append("portal_fallback" if used else "kernel_ok")

    def executable(self) -> bool:
        required = ["fail_closed", "restart_reload_halt", "reconcile"]
        return all(step in self.steps for step in required)
