"""Additional DR scenario harnesses (**§14.2**)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BrokerOutageDrill:
    steps: list[str] = field(default_factory=list)

    def exercise(self) -> None:
        self.steps.append("preserve_last_known")
        self.steps.append("no_invented_state")
        self.steps.append("wait_broker_playbook")

    def gate_met(self) -> bool:
        return len(self.steps) == 3


@dataclass
class HostFailureDrill:
    steps: list[str] = field(default_factory=list)

    def exercise(self, *, signatures_ok: bool, reconciled: bool) -> None:
        if not signatures_ok:
            raise ValueError("approved artifact signatures required")
        self.steps.append("restore_artifact")
        if not reconciled:
            raise ValueError("reconcile before resume")
        self.steps.append("reconcile_clean")
        self.steps.append("resume_risk_increasing")

    def gate_met(self) -> bool:
        return self.steps == ["restore_artifact", "reconcile_clean", "resume_risk_increasing"]
