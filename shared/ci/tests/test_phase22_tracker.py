"""Phase 22 exit evidence."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class Phase22TrackerTests(unittest.TestCase):
    def test_tracker_and_evidence_exist(self) -> None:
        tracker = json.loads((ROOT / "shared" / "ci" / "phase-22-tracker.json").read_text(encoding="utf-8"))
        self.assertEqual(tracker["phase"], 22)
        exit_criteria = tracker["exit_criteria"]
        self.assertTrue(exit_criteria["a_p1_01_adequacy_report"])
        self.assertTrue(exit_criteria["scenario_suite_green_staging"])
        self.assertTrue(exit_criteria["fact_log_evidence_extract"])
        self.assertTrue(exit_criteria["scenario_executable_ts04_ts10_am_oc_bf"])
        self.assertTrue(exit_criteria["a_dec_03_sim04_blocked_not_invented"])
        self.assertIn("A-DEC-03", tracker["blockers"])
        for rel in tracker["evidence"]:
            self.assertTrue((ROOT / rel).is_file(), rel)


if __name__ == "__main__":
    unittest.main()
