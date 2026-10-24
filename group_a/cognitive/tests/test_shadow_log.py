import sqlite3
import unittest

from sate_factlog.log import FactLog

from sate_cognitive.ingest import IngestResult
from sate_cognitive.shadow import ShadowAccumulator
from sate_cognitive.shadow_log import persist_ingest, persist_weekly_shadow


class ShadowLogTests(unittest.TestCase):
    def test_advisory_signal_events(self) -> None:
        log = FactLog(sqlite3.connect(":memory:"), writers=frozenset({"cognitive-a"}))
        result = IngestResult(ok=True, shadow_q=0.1, shadow_c=0.2, trading_view=None, reason="active")
        persist_ingest(
            log,
            event_id="ing-1",
            signal_id="sig-1",
            result=result,
            at="2026-10-23T12:00:00Z",
            correlation_id="s-1",
        )
        acc = ShadowAccumulator(week="2026-W43")
        acc.record_ingest(ok=True, signal_id="a", shadow_q=0.1, shadow_c=0.2)
        acc.record_ingest(ok=True, signal_id="b", shadow_q=-0.1, shadow_c=0.2)
        acc.attach_outcome("a", 1.0)
        acc.attach_outcome("b", -1.0)
        persist_weekly_shadow(
            log,
            event_id="wk-1",
            report=acc.weekly_report(),
            at="2026-10-23T12:00:00Z",
        )
        rows = log.poll(after_seq=0, group_scope="A", reader_id="cognitive-a")
        self.assertEqual(len(rows), 2)


if __name__ == "__main__":
    unittest.main()
