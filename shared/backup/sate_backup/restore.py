"""Restore to clean host and verify hash chain."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from sate_factlog.log import FactLog

from sate_backup.snapshot import decrypt_backup


def restore_and_verify(encrypted_backup: Path, *, key: bytes, reader_id: str = "backup") -> dict[str, object]:
    plaintext = decrypt_backup(encrypted_backup, key=key)
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "restored.db"
        target.write_bytes(plaintext)
        conn = sqlite3.connect(str(target))
        try:
            log = FactLog(
                conn,
                writers=frozenset({"backup"}),
                readers=frozenset({reader_id, "backup"}),
                readonly=True,
            )
            broken = log.verify(reader_id=reader_id)
            return {
                "chain_ok": broken is None,
                "broken_seq": broken,
                "restored_path": str(target),
            }
        finally:
            conn.close()
