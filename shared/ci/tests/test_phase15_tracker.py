"""Phase 15 exit evidence."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class Phase15TrackerTests(unittest.TestCase):
    def test_tracker_and_evidence_exist(self) -> None:
        tracker = json.loads((ROOT / "shared" / "ci" / "phase-15-tracker.json").read_text(encoding="utf-8"))
        self.assertEqual(tracker["phase"], 15)
        self.assertIn("A-P0-14", tracker["backlog_complete"])
        exit_criteria = tracker["exit_criteria"]
        self.assertTrue(exit_criteria["kill_k1_k2_k3_sim_drill"])
        self.assertTrue(exit_criteria["global_halt_inv06"])
        for rel in tracker["evidence"]:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_inv06_is_enforced_in_the_coordinator(self) -> None:
        text = (ROOT / "shared" / "halt-coordinator" / "sate_halt" / "protocol.py").read_text(encoding="utf-8")
        self.assertIn("HALT_CONFIRMED_ALL", text)
        self.assertIn("b_reachable", text)


if __name__ == "__main__":
    unittest.main()
