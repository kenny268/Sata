"""Phase 25 exit evidence."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class Phase25TrackerTests(unittest.TestCase):
    def test_tracker_and_evidence_exist(self) -> None:
        tracker = json.loads((ROOT / "shared" / "ci" / "phase-25-tracker.json").read_text(encoding="utf-8"))
        self.assertEqual(tracker["phase"], 25)
        exit_criteria = tracker["exit_criteria"]
        self.assertTrue(exit_criteria["a_p1_06_live_preflight_engine"])
        self.assertFalse(exit_criteria["numeric_rpo_rto_owner_set"])
        for rel in tracker["evidence"]:
            self.assertTrue((ROOT / rel).is_file(), rel)


if __name__ == "__main__":
    unittest.main()
