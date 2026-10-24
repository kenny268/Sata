"""Phase 19 exit evidence."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


class Phase19TrackerTests(unittest.TestCase):
    def test_tracker_and_evidence_exist(self) -> None:
        tracker = json.loads((ROOT / "shared" / "ci" / "phase-19-tracker.json").read_text(encoding="utf-8"))
        self.assertEqual(tracker["phase"], 19)
        exit_criteria = tracker["exit_criteria"]
        self.assertTrue(exit_criteria["critical_alert_non_suppressible"])
        self.assertTrue(exit_criteria["backup_restore_chain_verify"])
        self.assertTrue(exit_criteria["kernel_stall_alert_60s"])
        self.assertTrue(exit_criteria["mt5_bridge_monitored"])
        self.assertTrue(exit_criteria["slo_on_call_routing"])
        self.assertTrue(exit_criteria["appendix_d_licence_hooks"])
        self.assertTrue(exit_criteria["a_log_04_cold_archive"])
        self.assertTrue(exit_criteria["rpo_rto_harness"])
        self.assertTrue(exit_criteria["runbook_c2_ops_drill"])
        self.assertTrue(exit_criteria["tg_po_15_monitoring_wire"])
        self.assertTrue(exit_criteria["control_api_security_alerts"])
        self.assertTrue(exit_criteria["off_host_backup_runner"])
        self.assertTrue(exit_criteria["observables_full_registry"])
        self.assertFalse(exit_criteria["numeric_rpo_rto_owner_set"])
        self.assertFalse(exit_criteria["windows_host_provisioned"])
        for rel in tracker["evidence"]:
            self.assertTrue((ROOT / rel).is_file(), rel)


if __name__ == "__main__":
    unittest.main()
