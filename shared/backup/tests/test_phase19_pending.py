import sqlite3
import tempfile
import unittest
from pathlib import Path

from cryptography.fernet import Fernet
from sate_factlog.log import FactLog

from sate_backup.cold_archive import archive_fact_log, reconstruct_path
from sate_backup.job import BackupJob
from sate_backup.monthly_drill import run_monthly_drill
from sate_backup.rpo_rto import load_register, validate_register


class BackupPhase19PendingTests(unittest.TestCase):
    def test_cold_archive_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "fact.db"
            gz = root / "fact.db.gz"
            conn = sqlite3.connect(str(db))
            log = FactLog(conn, writers=frozenset({"backup"}))
            log._conn.close()
            archive_fact_log(db, gz, chain_head="abc", decision_ref="docs/design/group_a/decision-log.md")
            manifest = gz.with_suffix(".manifest.json")
            self.assertTrue(manifest.is_file())
            self.assertTrue(reconstruct_path(manifest).is_file())

    def test_backup_job_metrics(self) -> None:
        key = Fernet.generate_key()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db = root / "fact.db"
            enc = root / "fact.db.enc"
            conn = sqlite3.connect(str(db))
            log = FactLog(conn, writers=frozenset({"backup"}))
            log._conn.close()
            job = BackupJob(source_db=db, destination=enc, key=key)
            job.run(at="2026-10-23T12:00:00Z")
            metric = job.metric()
            self.assertIsNotNone(metric["backup_last_success"])

    def test_rpo_rto_harness_unset(self) -> None:
        root = Path(__file__).resolve().parents[3]
        data = load_register(root / "shared" / "ci" / "a-dec-09-rpo-rto.json")
        result = validate_register(data)
        self.assertFalse(result["owner_set"])

    def test_monthly_drill_orchestrator(self) -> None:
        drill = run_monthly_drill(month="2026-10")
        self.assertTrue(drill.gate_met())


if __name__ == "__main__":
    unittest.main()
