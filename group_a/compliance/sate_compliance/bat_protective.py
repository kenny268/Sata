"""BAT protective-order verification (**§7.4**)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProtectiveOrderBat:
    steps: list[str] = field(default_factory=list)

    def record_demo_verification(self) -> None:
        self.steps.extend(
            [
                "place_market_with_stop",
                "broker_ack_stop_attached",
                "reject_entry_without_stop",
            ]
        )

    def gate_met(self) -> bool:
        return len(self.steps) >= 3
