"""Monthly restore drill evidence (**§14.2**)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RestoreDrillLog:
    completed: list[str] = field(default_factory=list)

    def record(self, *, month: str, chain_ok: bool, clean_host: bool) -> None:
        if not clean_host:
            raise ValueError("restore drill requires a clean host")
        if not chain_ok:
            raise ValueError("hash chain must verify after restore")
        self.completed.append(month)

    def gate_met(self, *, minimum_months: int = 1) -> bool:
        return len(self.completed) >= minimum_months
