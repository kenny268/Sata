"""Alert severity and routing (**A-P0-17**, §14.1)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CriticalAlert:
    group_scope: str
    code: str
    message: str
    severity: str = "CRITICAL"


@dataclass
class AlertRouter:
    delivered: list[CriticalAlert] = field(default_factory=list)
    suppressed_notice: int = 0

    def route(self, alert: CriticalAlert, *, muted: bool = False) -> bool:
        if alert.severity == "CRITICAL":
            self.delivered.append(alert)
            return True
        if alert.severity == "NOTICE" and muted:
            self.suppressed_notice += 1
            return False
        self.delivered.append(alert)
        return True
