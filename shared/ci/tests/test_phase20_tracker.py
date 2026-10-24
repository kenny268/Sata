"""Phase 20 exit evidence."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class Phase20TrackerTests(unittest.TestCase):
    def test_tracker_and_evidence_exist(self) -> None:
        tracker = json.loads((ROOT / "shared" / "ci" / "phase-20-tracker.json").read_text(encoding="utf-8"))
        self.assertEqual(tracker["phase"], 20)
        exit_criteria = tracker["exit_criteria"]
        self.assertTrue(exit_criteria["intent_schema_validated"])
        self.assertTrue(exit_criteria["four_week_sim_evidence_harness"])
        self.assertTrue(exit_criteria["four_weeks_automated_demo_sessions"])
        self.assertTrue(exit_criteria["journal_completeness_100_marathon"])
        self.assertTrue(exit_criteria["pre_kernel_validation"])
        self.assertTrue(exit_criteria["ts_scenarios_ts01_ts03_ts09"])
        self.assertTrue(exit_criteria["continuous_sim_runner"])
        self.assertFalse(exit_criteria["four_weeks_exness_windows_host_marathon"])
        for rel in tracker["evidence"]:
            self.assertTrue((ROOT / rel).is_file(), rel)


if __name__ == "__main__":
    unittest.main()
