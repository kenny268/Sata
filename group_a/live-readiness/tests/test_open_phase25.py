import os
import sqlite3
import unittest

from sate_control.auth import Session
from sate_control.router import ControlApi
from sate_factlog.log import FactLog

from sate_live_readiness.live_ops_wire import inputs_for_arm, seed_staging_live_readiness
from sate_live_readiness.phase25_gate import build_phase25_report, staging_complete_report
from sate_live_readiness.preflight_engine import assess_live_readiness
from sate_live_readiness.verification_matrix import load_matrix

_PASSKEY = "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGWFiY2RlZmdoaWprbG1ub3BxcnN0dXZ3eHk"


class OpenPhase25Tests(unittest.TestCase):
    def test_verification_matrix_covers_all_classes(self) -> None:
        matrix = load_matrix()
        classes = matrix["classes"]
        self.assertEqual(
            set(classes),
            {"UT", "IT", "BAT", "REC", "STM", "INV", "SEC", "RT", "FI", "DR", "DEP", "TRE", "HALT", "ISO", "PERF", "MOD", "OPS", "TG"},
        )

    def test_staging_complete_report(self) -> None:
        report = staging_complete_report()
        self.assertTrue(report["a_p1_06_preflight_ok"])

    def test_inputs_from_fact_log_without_staging_flag(self) -> None:
        log = FactLog(
            sqlite3.connect(":memory:"),
            writers=frozenset({"compliance-a", "live-readiness-a", "sim-ops-a", "strategy-a"}),
            readers=frozenset({"compliance-a", "live-readiness-a", "sim-ops-a", "control-api"}),
        )
        at = "2026-10-23T21:00:00Z"
        seed_staging_live_readiness(log, at=at)
        inputs = inputs_for_arm({}, log=log, as_of=at, broker_preflight_ok=True)
        assessment = assess_live_readiness(inputs)
        self.assertFalse(assessment.block_reasons())

    def test_full_arm_from_fact_log_only(self) -> None:
        log = FactLog(
            sqlite3.connect(":memory:"),
            writers=frozenset({"compliance-a", "control-api", "live-readiness-a", "sim-ops-a", "strategy-a"}),
            readers=frozenset({"compliance-a", "control-api", "live-readiness-a", "sim-ops-a", "test"}),
        )
        at = "2026-10-23T21:00:00Z"
        seed_staging_live_readiness(log, at=at)
        api = ControlApi(log=log, session=Session(principal="owner", group_scope="A"), now=at)
        result = api.dispatch(
            "POST",
            "/mode/A/arm",
            {"passkey_assertion": _PASSKEY, "otp": "999999", "as_of": at},
            csrf_token=api.issue_csrf()["csrf_token"],
        )
        self.assertEqual(result["status"], "arming")

    def test_phase25_report_from_log(self) -> None:
        log = FactLog(
            sqlite3.connect(":memory:"),
            writers=frozenset({"live-readiness-a"}),
            readers=frozenset({"live-readiness-a"}),
        )
        report = build_phase25_report(log, as_of="2026-10-23T21:00:00Z")
        self.assertFalse(report["a_p1_06_preflight_ok"])
        os.environ["SATE_RPO_MINUTES"] = "15"
        os.environ["SATE_RTO_MINUTES"] = "60"
        os.environ["SATE_CG_LIVE_INITIAL_ADVISORY_ZERO"] = "true"
        try:
            report2 = staging_complete_report()
            self.assertTrue(report2["phase25_exit_met"])
        finally:
            os.environ.pop("SATE_RPO_MINUTES", None)
            os.environ.pop("SATE_RTO_MINUTES", None)
            os.environ.pop("SATE_CG_LIVE_INITIAL_ADVISORY_ZERO", None)


if __name__ == "__main__":
    unittest.main()
