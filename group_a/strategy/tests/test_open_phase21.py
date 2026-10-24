import sqlite3
import tempfile
import unittest
from pathlib import Path

from sate_cognitive.shadow_store import load_accumulator
from sate_cognitive.weekly_runner import run_weekly_from_state
from sate_factlog.log import FactLog

from sate_strategy_a.demo_marathon import run_demo_marathon


class OpenPhase21Tests(unittest.TestCase):
    def test_marathon_shadow_state_and_weekly_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            report_dir = Path(tmp) / "reports"
            import os

            os.environ["SATE_SHADOW_STATE_FILE"] = str(state)
            os.environ["SATE_SHADOW_REPORT_DIR"] = str(report_dir)
            at = "2026-10-23T21:00:00Z"
            log = FactLog(
                sqlite3.connect(":memory:"),
                writers=frozenset({"strategy-a", "kernel-a", "cognitive-a"}),
                readers=frozenset({"strategy-a", "cognitive-a"}),
            )
            run_demo_marathon(weeks=1, sessions_per_week=7, at=at, log=log)
            self.assertTrue(state.is_file())
            acc = load_accumulator(state)
            self.assertGreater(acc.ingested, 0)
            self.assertGreater(acc.abstains, 0)
            report = run_weekly_from_state(week="2026-W43", state_file=state)
            self.assertIsNotNone(report.mean_shadow_c)
            exported = list(report_dir.glob("shadow-*.json"))
            self.assertEqual(len(exported), 1)
            rows = log.poll(after_seq=0, group_scope="A", reader_id="cognitive-a")
            kinds = {row.payload.get("kind") for row in rows}
            self.assertIn("ingest", kinds)
            self.assertIn("weekly_shadow", kinds)


if __name__ == "__main__":
    unittest.main()
