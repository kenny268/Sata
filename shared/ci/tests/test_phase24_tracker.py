"""Phase 24 exit evidence."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class Phase24TrackerTests(unittest.TestCase):
    def test_tracker_and_evidence_exist(self) -> None:
        tracker = json.loads((ROOT / "shared" / "ci" / "phase-24-tracker.json").read_text(encoding="utf-8"))
        self.assertEqual(tracker["phase"], 24)
        exit_criteria = tracker["exit_criteria"]
        self.assertTrue(exit_criteria["preflight_broker_gate_wired"])
        self.assertFalse(exit_criteria["kenya_exness_written_verification_on_file"])
        for rel in tracker["evidence"]:
            self.assertTrue((ROOT / rel).is_file(), rel)


if __name__ == "__main__":
    unittest.main()
