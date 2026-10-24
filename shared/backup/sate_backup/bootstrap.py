"""Compose smoke: encrypt, restore, verify chain."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet
from sate_factlog.log import FactLog

from sate_backup.drill import RestoreDrillLog
from sate_backup.restore import restore_and_verify
from sate_backup.snapshot import create_encrypted_backup


def main() -> None:
    key = Fernet.generate_key()
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "fact.db"
        enc = Path(tmp) / "fact.db.enc"
        log = FactLog(sqlite3.connect(str(db)), writers=frozenset({"backup"}))
        log.append(
            event_id="e-1",
            event_type="deployment",
            group_scope="A",
            occurred_at="2026-10-23T00:00:00Z",
            recorded_at="2026-10-23T00:00:00Z",
            correlation_id="drill-1",
            writer_id="backup",
            payload={"artifact": "staging", "version": "1"},
        )
        create_encrypted_backup(db, enc, key=key)
        result = restore_and_verify(enc, key=key)
        if not result["chain_ok"]:
            raise SystemExit("chain verify failed")
        drill = RestoreDrillLog()
        drill.record(month="2026-10", chain_ok=True, clean_host=True)
        if not drill.gate_met():
            raise SystemExit("drill log incomplete")
    print("backup ok")


if __name__ == "__main__":
    main()
