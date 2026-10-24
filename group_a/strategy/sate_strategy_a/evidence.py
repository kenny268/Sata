"""SIM session evidence for Phase 20 exit criteria."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SimSessionRecord:
    session_id: str
    journal_logged: bool
    verdict: str
    order_placed: bool
    stop_attached: bool
    intent_id: str | None = None


@dataclass
class SimWeekEvidence:
    weeks: list[list[SimSessionRecord]] = field(default_factory=list)

    def record_week(self, sessions: list[SimSessionRecord]) -> None:
        self.weeks.append(sessions)

    def journal_completeness(self) -> float:
        total = sum(len(week) for week in self.weeks)
        if total == 0:
            return 0.0
        logged = sum(1 for week in self.weeks for session in week if session.journal_logged)
        return logged / total

    def gate_met(self, *, minimum_weeks: int = 4, sessions_per_week: int = 5) -> bool:
        if len(self.weeks) < minimum_weeks:
            return False
        if any(len(week) < sessions_per_week for week in self.weeks):
            return False
        if self.journal_completeness() < 1.0:
            return False
        traded = [
            session
            for week in self.weeks
            for session in week
            if session.verdict in {"Allow", "AllowWithSize"}
        ]
        if not traded:
            return False
        return all(session.order_placed and session.stop_attached for session in traded)
