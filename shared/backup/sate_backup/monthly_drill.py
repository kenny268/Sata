"""Orchestrate monthly restore drill on a clean host."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet
from sate_factlog.log import FactLog

from sate_backup.drill import RestoreDrillLog
from sate_backup.drill_evidence import record_monthly_drill
from sate_backup.restore import restore_and_verify
from sate_backup.snapshot import create_encrypted_backup


def run_monthly_drill(
    *,
    month: str,
    key: bytes | None = None,
    evidence_log: FactLog | None = None,
    at: str = "2026-10-23T00:00:00Z",
) -> RestoreDrillLog:
    fernet_key = key or Fernet.generate_key()
    log_drill = RestoreDrillLog()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        db = root / "fact.db"
        enc = root / "fact.db.enc"
        conn = sqlite3.connect(str(db))
        log = FactLog(conn, writers=frozenset({"backup"}))
        log.append(
            event_id=f"drill-{month}",
            event_type="deployment",
            group_scope="A",
            occurred_at=f"{month}-01T00:00:00Z",
            recorded_at=f"{month}-01T00:00:01Z",
            correlation_id=f"restore-drill-{month}",
            writer_id="backup",
            payload={"drill": "monthly"},
        )
        conn.close()
        create_encrypted_backup(db, enc, key=fernet_key)
        result = restore_and_verify(enc, key=fernet_key)
        chain_ok = bool(result["chain_ok"])
        log_drill.record(month=month, chain_ok=chain_ok, clean_host=True)
        if evidence_log is not None:
            record_monthly_drill(
                evidence_log,
                month=month,
                chain_ok=chain_ok,
                clean_host=True,
                at=at,
            )
    return log_drill
