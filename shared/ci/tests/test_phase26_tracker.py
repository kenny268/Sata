"""Phase 26 exit evidence."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class Phase26TrackerTests(unittest.TestCase):
    def test_tracker_and_evidence_exist(self) -> None:
        tracker = json.loads((ROOT / "shared" / "ci" / "phase-26-tracker.json").read_text(encoding="utf-8"))
        self.assertEqual(tracker["phase"], 26)
        self.assertFalse(tracker["exit_criteria"]["first_production_session_on_broker"])
        for rel in tracker["evidence"]:
            self.assertTrue((ROOT / rel).is_file(), rel)


if __name__ == "__main__":
    unittest.main()
