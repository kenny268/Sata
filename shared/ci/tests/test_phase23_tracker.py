"""Phase 23 exit evidence."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class Phase23TrackerTests(unittest.TestCase):
    def test_tracker_and_evidence_exist(self) -> None:
        tracker = json.loads((ROOT / "shared" / "ci" / "phase-23-tracker.json").read_text(encoding="utf-8"))
        self.assertEqual(tracker["phase"], 23)
        exit_criteria = tracker["exit_criteria"]
        self.assertTrue(exit_criteria["accelerated_six_month_harness"])
        self.assertTrue(exit_criteria["sim_runner_ledger_wire"])
        self.assertFalse(exit_criteria["six_month_wall_clock_elapsed"])
        self.assertIn("A-SIM-01", tracker["backlog_complete"])
        for rel in tracker["evidence"]:
            self.assertTrue((ROOT / rel).is_file(), rel)


if __name__ == "__main__":
    unittest.main()
