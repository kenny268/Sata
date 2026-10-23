"""Kill drill scheduling (**A-KIL-06**)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DrillLog:
    channels: set[str] = field(default_factory=set)
    levels: set[str] = field(default_factory=set)

    def record(self, *, channel: str, kill_level: str, mode: str) -> None:
        if mode != "SIM":
            raise ValueError("kill drills stay on SIM")
        if kill_level not in {"K1", "K2", "K3"}:
            raise ValueError("kill level must be K1, K2, or K3")
        self.channels.add(channel)
        self.levels.add(kill_level)

    def gate_met(self) -> bool:
        required_channels = {"telegram", "web", "cli", "trusted_contact"}
        required_levels = {"K1", "K2", "K3"}
        return required_channels <= self.channels and required_levels <= self.levels
