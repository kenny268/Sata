"""Runbook **C.6** check-in lapsed (**OP-01**–**OP-03**)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class C6Runbook:
    steps: list[str] = field(default_factory=list)

    def step1_day7_presence(self, *, channel: str) -> None:
        if channel not in {"telegram_alive", "web_passkey"}:
            raise ValueError("day 7 presence requires /alive or web passkey")
        self.steps.append("day7_presence")

    def step2_day10_lift(self, *, checked_in_on_web: bool) -> None:
        if not checked_in_on_web:
            raise ValueError("MANAGE_ONLY lifts only after a web check-in")
        self.steps.append("day10_lift")

    def step3_day14_recovery(self, *, rearm_started: bool) -> None:
        if not rearm_started:
            raise ValueError("day 14 flatten recovery follows C.5 re-arm")
        self.steps.append("day14_recovery")

    def executable(self) -> bool:
        required = ["day7_presence", "day10_lift", "day14_recovery"]
        return self.steps == required
