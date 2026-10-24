import sqlite3
import unittest

from sate_factlog.log import FactLog
from sate_strategy_a.demo_marathon import run_demo_marathon

from sate_adequacy.fact_extract import evidence_from_fact_log
from sate_adequacy.report import build_adequacy_report


class FactExtractTests(unittest.TestCase):
    def test_demo_marathon_fact_log_feeds_report(self) -> None:
        log = FactLog(
            sqlite3.connect(":memory:"),
            writers=frozenset({"strategy-a", "kernel-a", "cognitive-a", "adequacy-a"}),
            readers=frozenset({"strategy-a", "cognitive-a", "adequacy-a"}),
        )
        at = "2026-10-23T21:00:00Z"
        run_demo_marathon(weeks=1, sessions_per_week=3, at=at, log=log)
        evidence = evidence_from_fact_log(
            log,
            reader_id="adequacy-a",
            as_of=at,
            sim_months_continuous=6.5,
        )
        report = build_adequacy_report(evidence)
        self.assertIn("performance_dashboard", report)
        self.assertTrue(report["software_ready"])


if __name__ == "__main__":
    unittest.main()
