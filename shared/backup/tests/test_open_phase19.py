import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from cryptography.fernet import Fernet
from sate_factlog.log import FactLog

from sate_backup.drill_evidence import record_monthly_drill
from sate_backup.monthly_drill import run_monthly_drill
from sate_backup.off_host import copy_off_host
from sate_backup.rpo_rto import load_register, merge_deploy_overrides, validate_register
from sate_backup.runner import run_scheduled_backup


class OpenPhase19BackupTests(unittest.TestCase):
    def test_off_host_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            enc = root / "fact.db.enc"
            enc.write_bytes(b"cipher")
            remote = root / "remote"
            copied = copy_off_host(enc, remote)
            self.assertTrue(copied.is_file())

    def test_runner_and_remote(self) -> None:
        key = Fernet.generate_key()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "fact.db"
            conn = sqlite3.connect(str(db))
            log = FactLog(conn, writers=frozenset({"backup"}))
            log._conn.close()
            backup_dir = root / "backups"
            remote = root / "offhost"
            os.environ["SATE_BACKUP_KEY"] = key.decode()
            os.environ["SATE_FACTLOG_DB"] = str(db)
            os.environ["SATE_BACKUP_DIR"] = str(backup_dir)
            os.environ["SATE_BACKUP_REMOTE_DIR"] = str(remote)
            try:
                metric = run_scheduled_backup()
                self.assertIsNotNone(metric["backup_last_success"])
                self.assertIsNotNone(metric["off_host_path"])
            finally:
                for name in (
                    "SATE_BACKUP_KEY",
                    "SATE_FACTLOG_DB",
                    "SATE_BACKUP_DIR",
                    "SATE_BACKUP_REMOTE_DIR",
                ):
                    os.environ.pop(name, None)

    def test_rpo_rto_env_override(self) -> None:
        root = Path(__file__).resolve().parents[3]
        data = load_register(root / "shared" / "ci" / "a-dec-09-rpo-rto.json")
        os.environ["SATE_RPO_MINUTES"] = "15"
        os.environ["SATE_RTO_MINUTES"] = "60"
        try:
            merged = merge_deploy_overrides(data)
            result = validate_register(merged)
            self.assertTrue(result["owner_set"])
            self.assertFalse(result["live_gate_blocked_until_set"])
        finally:
            os.environ.pop("SATE_RPO_MINUTES", None)
            os.environ.pop("SATE_RTO_MINUTES", None)

    def test_monthly_drill_factlog_evidence(self) -> None:
        log = FactLog(sqlite3.connect(":memory:"), writers=frozenset({"backup"}))
        run_monthly_drill(month="2026-11", evidence_log=log, at="2026-11-01T00:00:00Z")
        rows = log.poll(after_seq=0, group_scope="A", reader_id="backup")
        self.assertEqual(rows[0].payload["drill"], "monthly_restore")

    def test_drill_evidence_direct(self) -> None:
        log = FactLog(sqlite3.connect(":memory:"), writers=frozenset({"backup"}))
        record_monthly_drill(
            log,
            month="2026-12",
            chain_ok=True,
            clean_host=True,
            at="2026-12-01T00:00:00Z",
        )
        self.assertEqual(len(log.poll(after_seq=0, group_scope="A", reader_id="backup")), 1)


if __name__ == "__main__":
    unittest.main()
