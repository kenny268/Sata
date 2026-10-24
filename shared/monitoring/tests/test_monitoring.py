import sqlite3
import unittest

from sate_factlog.log import FactLog

from sate_monitoring.alerts import AlertRouter, CriticalAlert
from sate_monitoring.bridge import observe_bridge
from sate_monitoring.c2_runbook import C2Runbook
from sate_monitoring.factlog_watch import check_chain
from sate_monitoring.heartbeat import HeartbeatMonitor


class MonitoringTests(unittest.TestCase):
    def test_critical_never_suppressed_when_muted(self) -> None:
        router = AlertRouter()
        critical = CriticalAlert(group_scope="A", code="halt_uncertainty", message="test")
        notice = CriticalAlert(group_scope="A", code="cost_cap", message="warn", severity="NOTICE")
        self.assertTrue(router.route(critical, muted=True))
        self.assertFalse(router.route(notice, muted=True))
        self.assertEqual(len(router.delivered), 1)

    def test_kernel_stall_fires_within_budget(self) -> None:
        router = AlertRouter()
        monitor = HeartbeatMonitor(stall_threshold_sec=5.0, alert_budget_sec=60.0)
        monitor.beat(now=0.0)
        result = monitor.evaluate(now=40.0, router=router)
        self.assertTrue(result.detected)
        self.assertTrue(result.alert_fired)
        self.assertEqual(router.delivered[0].code, "kernel_heartbeat_lost")

    def test_bridge_observation(self) -> None:
        obs = observe_bridge(adapter_state="HEALTHY", poll_failures=0, latency_ms=12)
        self.assertEqual(obs.group_scope, "A")
        self.assertEqual(obs.adapter_state, "connected")

    def test_c2_runbook_executable(self) -> None:
        book = C2Runbook()
        book.step1_fail_closed()
        book.step2_restart_and_reload_halt(reloaded=True)
        book.step3_reconcile(clean=True)
        book.step4_manual_portal_if_needed(used=False)
        self.assertTrue(book.executable())

    def test_factlog_chain_break_emits_critical(self) -> None:
        log = FactLog(sqlite3.connect(":memory:"), writers=frozenset({"identity"}))
        log.append(
            event_id="e-1",
            event_type="alert",
            group_scope="A",
            occurred_at="2026-10-23T00:00:00Z",
            recorded_at="2026-10-23T00:00:01Z",
            correlation_id="c-1",
            writer_id="identity",
            payload={"ok": True},
        )
        router = AlertRouter()
        self.assertIsNone(check_chain(log, reader_id="identity", router=router))
        log._conn.execute("DROP TRIGGER events_no_update")
        log._conn.execute("UPDATE events SET event_hash = 'bad' WHERE seq = 1")
        log._conn.commit()
        broken = check_chain(log, reader_id="identity", router=router)
        self.assertEqual(broken, 1)
        self.assertEqual(router.delivered[0].code, "factlog_chain_broken")


if __name__ == "__main__":
    unittest.main()
