"""Regime filter **A-SIG-02** — tilt disabled when unstable or **N** unset."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RegimeFilter:
    unstable_limit: int | None
    unstable_sessions: int = 0

    def record(self, *, stable: bool) -> None:
        if stable:
            self.unstable_sessions = 0
            return
        self.unstable_sessions += 1

    def tilt_enabled(self) -> bool:
        if self.unstable_limit is None:
            return False
        return self.unstable_sessions < self.unstable_limit

    def should_abstain(self) -> bool:
        if self.unstable_limit is None:
            return False
        return self.unstable_sessions >= self.unstable_limit
