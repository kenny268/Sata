import sqlite3
import unittest
from pathlib import Path

from sate_factlog.log import FactLog

from sate_compliance.bat_protective import ProtectiveOrderBat
from sate_compliance.evidence import load_package
from sate_compliance.gate import assess_live_readiness
from sate_compliance.persist import persist_evidence_package, persist_sign_off
from sate_compliance.relay_policy import RelayPolicy
from sate_compliance.staging import complete_gate, incomplete_gate

ROOT = Path(__file__).resolve().parents[3]


class ComplianceTests(unittest.TestCase):
    def test_schema_example_loads(self) -> None:
        package = load_package(ROOT / "group_a" / "compliance" / "example" / "staging-evidence.json")
        self.assertTrue(package.known_rules_complete)

    def test_inv08_blocks_incomplete(self) -> None:
        reasons = incomplete_gate().block_reasons()
        self.assertIn("inv08_unknown_rules_disabled", reasons)

    def test_complete_gate_allows(self) -> None:
        self.assertFalse(complete_gate().block_reasons())

    def test_relay_sec_when_enabled(self) -> None:
        reasons = assess_live_readiness(
            package=complete_gate().package,
            blockers=complete_gate().blockers,
            sign_off=complete_gate().sign_off,
            tax_memo=complete_gate().tax_memo,
            relay=RelayPolicy(enabled=True, endpoint="", auth_method="", replay_policy=""),
            bat_protective_ok=True,
        )
        self.assertIn("a_dec_08_relay_policy_invalid", reasons)

    def test_bat_protective(self) -> None:
        bat = ProtectiveOrderBat()
        bat.record_demo_verification()
        self.assertTrue(bat.gate_met())

    def test_factlog_persist(self) -> None:
        log = FactLog(sqlite3.connect(":memory:"), writers=frozenset({"compliance-a"}))
        package = complete_gate().package
        assert package is not None
        persist_evidence_package(log, package, at="2026-10-23T00:00:00Z")
        sign_off = complete_gate().sign_off
        assert sign_off is not None
        persist_sign_off(log, sign_off, at="2026-10-23T00:00:00Z")
        rows = log.poll(after_seq=0, group_scope="A", reader_id="compliance-a")
        self.assertEqual(len(rows), 2)


if __name__ == "__main__":
    unittest.main()
