"""Phase 18 exit evidence."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class Phase18TrackerTests(unittest.TestCase):
    def test_tracker_and_evidence_exist(self) -> None:
        tracker = json.loads((ROOT / "shared" / "ci" / "phase-18-tracker.json").read_text(encoding="utf-8"))
        self.assertEqual(tracker["phase"], 18)
        exit_criteria = tracker["exit_criteria"]
        self.assertTrue(exit_criteria["negative_auth_suite"])
        self.assertTrue(exit_criteria["tg_po_01_10_delivered"])
        self.assertTrue(exit_criteria["tg_po_11_15"])
        self.assertTrue(exit_criteria["telegram_long_poll_runner"])
        for rel in tracker["evidence"]:
            self.assertTrue((ROOT / rel).is_file(), rel)


if __name__ == "__main__":
    unittest.main()
