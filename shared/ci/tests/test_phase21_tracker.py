"""Phase 21 exit evidence."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class Phase21TrackerTests(unittest.TestCase):
    def test_tracker_and_evidence_exist(self) -> None:
        tracker = json.loads((ROOT / "shared" / "ci" / "phase-21-tracker.json").read_text(encoding="utf-8"))
        self.assertEqual(tracker["phase"], 21)
        exit_criteria = tracker["exit_criteria"]
        self.assertTrue(exit_criteria["live_advisory_multiplier_zero"])
        self.assertTrue(exit_criteria["cg_live_threshold_not_invented"])
        self.assertTrue(exit_criteria["a_cog_04_shadow_weekly_export"])
        self.assertTrue(exit_criteria["sim_loop_shadow_accumulator"])
        self.assertTrue(exit_criteria["shadow_factlog_persist"])
        self.assertIn("A-COG-04", tracker["backlog_complete"])
        self.assertFalse(tracker["methodology"]["a_cog_04"].lower().startswith("threshold"))
        for rel in tracker["evidence"]:
            self.assertTrue((ROOT / rel).is_file(), rel)


if __name__ == "__main__":
    unittest.main()
