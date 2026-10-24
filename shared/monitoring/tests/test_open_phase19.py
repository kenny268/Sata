import sqlite3
import unittest

from sate_factlog.errors import FactLogWriteError
from sate_factlog.log import FactLog

from sate_monitoring.appendix_d import market_data_licence
from sate_monitoring.appendix_d_log import persist_assumption
from sate_monitoring.dr_drills import BrokerOutageDrill, HostFailureDrill
from sate_monitoring.export_metrics import render_prometheus
from sate_monitoring.factlog_write_alert import alert_on_write_failure
from sate_monitoring.observables import collect_observables
from sate_monitoring.on_call import OnCallRouter
from sate_monitoring.quiet_hours import deliver_during_quiet_hours, in_quiet_hours


class OpenPhase19MonitoringTests(unittest.TestCase):
    def test_observables_cover_domains(self) -> None:
        samples = collect_observables(
            {
                "group_scope": "A",
                "heartbeat_ok": True,
                "adapter_state": "HEALTHY",
                "backup_last_success": "2026-10-23T00:00:00Z",
            },
            observed_at="2026-10-23T12:00:00Z",
        )
        names = {sample.name for sample in samples}
        self.assertIn("kernel.heartbeat_ok", names)
        self.assertIn("backup.last_success_ok", names)
        text = render_prometheus(samples)
        self.assertIn('group_scope="A"', text)

    def test_quiet_hours_critical_bypass(self) -> None:
        self.assertTrue(in_quiet_hours(now_minutes=22 * 60, window="20:00-04:00"))
        self.assertTrue(deliver_during_quiet_hours("CRITICAL", quiet=True))
        self.assertFalse(deliver_during_quiet_hours("NOTICE", quiet=True))

    def test_factlog_write_alert(self) -> None:
        router = OnCallRouter()
        alert_on_write_failure(FactLogWriteError("blocked", policy="BLOCK"), router=router)
        self.assertEqual(router.router.delivered[0].severity, "CRITICAL")

    def test_appendix_d_persisted(self) -> None:
        log = FactLog(sqlite3.connect(":memory:"), writers=frozenset({"monitoring"}))
        entry = market_data_licence(vendor="Exness")
        persist_assumption(log, entry, event_id="app-d-1", at="2026-10-23T00:00:00Z")
        rows = log.poll(after_seq=0, group_scope="A", reader_id="monitoring")
        self.assertEqual(rows[0].payload["appendix_d"]["assumption_id"], "APP-D-DATA-01")

    def test_dr_drills(self) -> None:
        broker = BrokerOutageDrill()
        broker.exercise()
        self.assertTrue(broker.gate_met())
        host = HostFailureDrill()
        host.exercise(signatures_ok=True, reconciled=True)
        self.assertTrue(host.gate_met())


if __name__ == "__main__":
    unittest.main()
