from __future__ import annotations

import unittest

from sate_email.c6_runbook import C6Runbook
from sate_email.ops_drill import OpsDrillLog, exercise_op01_to_op06


class OpsAndC6Tests(unittest.TestCase):
    def test_op01_through_op06_gate_in_sim(self) -> None:
        log = OpsDrillLog()
        exercise_op01_to_op06(log)
        self.assertTrue(log.gate_met())

    def test_c6_runbook_is_executable(self) -> None:
        book = C6Runbook()
        book.step1_day7_presence(channel="telegram_alive")
        book.step2_day10_lift(checked_in_on_web=True)
        book.step3_day14_recovery(rearm_started=True)
        self.assertTrue(book.executable())


if __name__ == "__main__":
    unittest.main()
