import sqlite3
import tempfile
import unittest
from pathlib import Path

from cryptography.fernet import Fernet
from sate_factlog.log import FactLog

from sate_backup.drill import RestoreDrillLog
from sate_backup.restore import restore_and_verify
from sate_backup.snapshot import create_encrypted_backup, decrypt_backup


class BackupTests(unittest.TestCase):
    def test_encrypt_restore_verify_chain(self) -> None:
        key = Fernet.generate_key()
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "fact.db"
            enc = Path(tmp) / "fact.db.enc"
            log = FactLog(sqlite3.connect(str(db)), writers=frozenset({"backup"}))
            log.append(
                event_id="e-backup-1",
                event_type="deployment",
                group_scope="A",
                occurred_at="2026-10-23T00:00:00Z",
                recorded_at="2026-10-23T00:00:01Z",
                correlation_id="corr-backup",
                writer_id="backup",
                payload={"artifact": "kernel-a"},
            )
            log._conn.close()
            create_encrypted_backup(db, enc, key=key)
            roundtrip = decrypt_backup(enc, key=key)
            self.assertEqual(roundtrip, db.read_bytes())
            result = restore_and_verify(enc, key=key)
            self.assertTrue(result["chain_ok"])

    def test_restore_drill_log(self) -> None:
        drill = RestoreDrillLog()
        drill.record(month="2026-10", chain_ok=True, clean_host=True)
        self.assertTrue(drill.gate_met())


if __name__ == "__main__":
    unittest.main()
