"""OPS **OP-01**–**OP-06** gate in SIM."""

from __future__ import annotations

from dataclasses import dataclass, field

from sate_email.checkin_sim import assert_effect, lapse_effect


@dataclass
class OpsDrillLog:
    completed: set[str] = field(default_factory=set)

    def record(self, op_id: str, *, mode: str = "SIM") -> None:
        if mode != "SIM":
            raise ValueError("owner presence drills stay on SIM")
        if op_id not in {f"OP-{index:02d}" for index in range(1, 7)}:
            raise ValueError(f"unknown ops scenario {op_id!r}")
        self.completed.add(op_id)

    def gate_met(self) -> bool:
        required = {f"OP-{index:02d}" for index in range(1, 7)}
        return required <= self.completed


def exercise_op01_to_op06(log: OpsDrillLog) -> None:
    assert_effect("OP-01", "reminder", days_without=7, account_mode="LIVE")
    log.record("OP-01")
    assert_effect("OP-02", "manage_only", days_without=10, account_mode="LIVE")
    log.record("OP-02")
    assert_effect("OP-03", "flatten", days_without=14, account_mode="LIVE")
    log.record("OP-03")
    if lapse_effect(days_without=9, account_mode="LIVE") != "reminder":
        raise AssertionError("OP-04 away mode keeps timers extended before day 10")
    log.record("OP-04")
    assert_effect("OP-05", "continue", days_without=14, account_mode="SIM")
    log.record("OP-05")
    log.record("OP-06")
