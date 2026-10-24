"""Phase 17 exit evidence."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

_SPA_PAGES = (
    "Overview.tsx",
    "Capital.tsx",
    "Controls.tsx",
    "Constitution.tsx",
    "Checkin.tsx",
    "Risk.tsx",
    "Reporting.tsx",
)


class Phase17TrackerTests(unittest.TestCase):
    def test_tracker_and_evidence_exist(self) -> None:
        tracker = json.loads((ROOT / "shared" / "ci" / "phase-17-tracker.json").read_text(encoding="utf-8"))
        self.assertEqual(tracker["phase"], 17)
        self.assertIn("A-P0-16", tracker["backlog_complete"])
        exit_criteria = tracker["exit_criteria"]
        self.assertTrue(exit_criteria["control_actions_in_fact_log"])
        self.assertTrue(exit_criteria["http_control_boundary"])
        self.assertTrue(exit_criteria["csrf_on_control_posts"])
        self.assertFalse(exit_criteria["live_final_gate"])
        for rel in tracker["evidence"]:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_spa_has_required_owner_pages(self) -> None:
        pages = ROOT / "shared" / "web" / "src" / "pages"
        for name in _SPA_PAGES:
            self.assertTrue((pages / name).is_file(), name)

    def test_router_declares_core_post_routes(self) -> None:
        text = (ROOT / "shared" / "control-api" / "sate_control" / "router.py").read_text(encoding="utf-8")
        for path in ("/mode/A/arm", "/checkin", "/capital/ratify", "/kill"):
            self.assertIn(path, text)


if __name__ == "__main__":
    unittest.main()
