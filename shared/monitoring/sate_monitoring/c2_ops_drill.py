"""OPS drill for runbook **C.2** (kernel heartbeat lost)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sate_monitoring.c2_runbook import C2Runbook


@dataclass
class C2OpsDrillLog:
    steps: list[str] = field(default_factory=list)

    def exercise(self) -> None:
        book = C2Runbook()
        book.step1_fail_closed()
        self.steps.append("fail_closed")
        book.step2_restart_and_reload_halt(reloaded=True)
        self.steps.append("restart_reload_halt")
        book.step3_reconcile(clean=True)
        self.steps.append("reconcile")
        book.step4_manual_portal_if_needed(used=False)
        self.steps.append("kernel_ok")
        if not book.executable():
            raise RuntimeError("C.2 runbook did not complete")

    def gate_met(self) -> bool:
        required = {"fail_closed", "restart_reload_halt", "reconcile"}
        return required.issubset(set(self.steps))
