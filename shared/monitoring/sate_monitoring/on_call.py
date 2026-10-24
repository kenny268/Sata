"""On-call routing: CRITICAL never suppressed; HIGH deduplicated (**§14.1**)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sate_monitoring.alerts import AlertRouter, CriticalAlert


@dataclass
class OnCallRouter:
    channels: tuple[str, ...] = ("telegram", "email")
    router: AlertRouter = field(default_factory=AlertRouter)
    _high_seen: set[str] = field(default_factory=set)
    dispatches: list[tuple[str, CriticalAlert]] = field(default_factory=list)

    def dispatch(self, alert: CriticalAlert, *, muted: bool = False) -> list[str]:
        if alert.severity == "HIGH":
            if alert.code in self._high_seen:
                return []
            self._high_seen.add(alert.code)
        if not self.router.route(alert, muted=muted):
            return []
        targets = list(self.channels) if alert.severity == "CRITICAL" else [self.channels[0]]
        for channel in targets:
            self.dispatches.append((channel, alert))
        return targets
