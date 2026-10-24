"""Model promotion infra **MP-01–03** (no live promotion in Phase 20)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PromotionInfraChecklist:
    items: list[str] = field(default_factory=list)

    def record_mp01_bootstrap_gate(self) -> None:
        self.items.append("MP-01")

    def record_mp02_shadow_decisions(self) -> None:
        self.items.append("MP-02")

    def record_mp03_no_loosen(self) -> None:
        self.items.append("MP-03")

    def gate_met(self) -> bool:
        return set(self.items) >= {"MP-01", "MP-02", "MP-03"}
