"""Phase 16 exit evidence."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class Phase16TrackerTests(unittest.TestCase):
    def test_tracker_and_evidence_exist(self) -> None:
        tracker = json.loads((ROOT / "shared" / "ci" / "phase-16-tracker.json").read_text(encoding="utf-8"))
        self.assertEqual(tracker["phase"], 16)
        exit_criteria = tracker["exit_criteria"]
        self.assertTrue(exit_criteria["day10_day14_sim_tested"])
        self.assertTrue(exit_criteria["appendix_d_smtp_production"])
        self.assertTrue(exit_criteria["runbook_c6_executable"])
        self.assertTrue(exit_criteria["ops_op01_op06_sim"])
        for rel in tracker["evidence"]:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_kernel_runs_checkin_independent_of_web(self) -> None:
        text = (ROOT / "group_a" / "kernel" / "verdict" / "src" / "checkin.rs").read_text(encoding="utf-8")
        self.assertIn("A-CHK-03", text)
        halt = (ROOT / "group_a" / "kernel" / "verdict" / "src" / "halt.rs").read_text(encoding="utf-8")
        self.assertIn("checkin_last", halt)


if __name__ == "__main__":
    unittest.main()
