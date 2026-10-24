import unittest

from sate_monitoring.alerts import CriticalAlert
from sate_monitoring.appendix_d import market_data_licence, news_licence
from sate_monitoring.c2_ops_drill import C2OpsDrillLog
from sate_monitoring.dashboard import build_panels
from sate_monitoring.on_call import OnCallRouter
from sate_monitoring.slo import slo_snapshot
from sate_monitoring.structured import emit
from sate_monitoring.tg_wire import to_health_payload


class Phase19PendingTests(unittest.TestCase):
    def test_on_call_critical_reaches_all_channels_when_muted(self) -> None:
        on_call = OnCallRouter(channels=("telegram", "email"))
        alert = CriticalAlert(group_scope="A", code="factlog_chain_broken", message="broken")
        targets = on_call.dispatch(alert, muted=True)
        self.assertEqual(targets, ["telegram", "email"])

    def test_high_is_deduplicated(self) -> None:
        on_call = OnCallRouter()
        alert = CriticalAlert(group_scope="A", code="recon_mismatch", message="x", severity="HIGH")
        self.assertEqual(len(on_call.dispatch(alert)), 1)
        self.assertEqual(on_call.dispatch(alert), [])

    def test_slo_and_dashboard(self) -> None:
        snap = slo_snapshot(kernel_stall_sec=30.0, bridge_latency_ms=100.0)
        self.assertTrue(snap["kernel_stall_ok"])
        panels = build_panels(kernel_stall_sec=30.0, bridge_latency_ms=100.0)
        self.assertTrue(all(panel.ok for panel in panels))

    def test_appendix_d_licence_hooks(self) -> None:
        data = market_data_licence(vendor="Exness feed terms")
        news = news_licence(vendor="Calendar provider")
        self.assertEqual(data["assumption_id"], "APP-D-DATA-01")
        self.assertEqual(news["assumption_id"], "APP-D-NEWS-01")

    def test_c2_ops_drill_gate(self) -> None:
        log = C2OpsDrillLog()
        log.exercise()
        self.assertTrue(log.gate_met())

    def test_tg_po_15_wire(self) -> None:
        alert = CriticalAlert(group_scope="A", code="kernel_heartbeat_lost", message="stale")
        payload = to_health_payload(alert)
        self.assertEqual(payload["category"], "HEALTH")
        self.assertIn("CRITICAL", payload["text"])

    def test_structured_emit(self) -> None:
        record = emit("monitoring", "backup_ok", group_scope="A", attempts=1)
        self.assertEqual(record.group_scope, "A")
        self.assertTrue(record.trace_id)


if __name__ == "__main__":
    unittest.main()
