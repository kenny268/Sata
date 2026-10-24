"""Phase 14 exit evidence. A failure means the tracker and build scope drifted apart."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class Phase14TrackerTests(unittest.TestCase):
    def test_tracker_and_evidence_exist(self) -> None:
        tracker_path = ROOT / "shared" / "ci" / "phase-14-tracker.json"
        tracker = json.loads(tracker_path.read_text(encoding="utf-8"))
        self.assertEqual(tracker["phase"], 14)
        self.assertIn("A-P0-13", tracker["backlog_complete"])
        self.assertTrue(tracker["a_dec_01_blocked"])
        self.assertTrue(tracker["a_p0_21_blocked"])
        self.assertFalse(tracker["demo_entries_without_verified_stop"])
        exit_criteria = tracker["exit_criteria"]
        self.assertTrue(exit_criteria["demo_zero_entries_without_verified_stop"])
        self.assertTrue(exit_criteria["stop_failure_reject_and_fact_log"])
        self.assertTrue(exit_criteria["kernel_enforcement_layer"])
        self.assertTrue(exit_criteria["rolling_slippage_window"])
        self.assertTrue(exit_criteria["scenario_harness_ts01_ts13"])
        self.assertTrue(exit_criteria["perf_slippage_measurement"])
        self.assertTrue(exit_criteria["bat_stop_attachment"])
        self.assertTrue(exit_criteria["kelly_upper_reference_only"])
        self.assertTrue(exit_criteria["cost_model_enforced"])
        self.assertFalse(tracker["slippage_measured_live"])
        for rel in tracker["evidence"]:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_kernel_enforces_phase14_guards(self) -> None:
        engine = (ROOT / "group_a" / "kernel" / "verdict" / "src" / "engine.rs").read_text(encoding="utf-8")
        for needle in (
            "protective_stop",
            "market_stale",
            "news_blackout",
            "swap_guard",
            "floor_to_step",
            "untradeable_at_this_capital",
            "slippage_window",
            "vol_scale",
            "ramp_factor",
            "kelly_ceiling",
            "wednesday_triple",
            "cost_model",
            "MinLotPolicy",
        ):
            self.assertIn(needle, engine, needle)
        slippage = (ROOT / "group_a" / "kernel" / "verdict" / "src" / "slippage.rs").read_text(encoding="utf-8")
        self.assertIn("WINDOW", slippage)
        self.assertIn("within_budget", slippage)
        self.assertIn("20", slippage)
        scenarios = (ROOT / "group_a" / "kernel" / "verdict" / "src" / "order_tests.rs").read_text(encoding="utf-8")
        for name in ("ts01_", "ts02_", "ts03_", "ts04_", "ts07_", "ts08_", "ts10", "ts11_"):
            self.assertIn(name, scenarios, name)
        bridge_tests = (ROOT / "group_a" / "broker" / "mt5-bridge" / "tests" / "test_bridge.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("test_bat_stop_attachment_is_verified_on_the_demo_terminal", bridge_tests)

    def test_bridge_and_journal_cover_stop_exit_criteria(self) -> None:
        bridge = (ROOT / "group_a" / "broker" / "mt5-bridge" / "sate_mt5_bridge" / "bridge.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("protective_stop", bridge)
        self.assertIn("stop_attached", bridge)
        journal = (ROOT / "group_a" / "runtime" / "sate_runtime" / "journal.py").read_text(encoding="utf-8")
        self.assertIn("persist_execution_failure", journal)
        self.assertIn("protective_stop", journal)

    def test_phase13_prerequisites_remain_documented(self) -> None:
        tracker = json.loads((ROOT / "shared" / "ci" / "phase-13-tracker.json").read_text(encoding="utf-8"))
        self.assertEqual(tracker["phase"], 13)


if __name__ == "__main__":
    unittest.main()
