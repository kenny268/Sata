"""Encrypted off-host backup (**A-P0-18**)."""

from __future__ import annotations

import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken


def load_key() -> bytes:
    raw = os.environ.get("SATE_BACKUP_KEY", "").strip()
    if not raw:
        raise ValueError("SATE_BACKUP_KEY is required for encrypted backups")
    return raw.encode()


def create_encrypted_backup(source_db: Path, destination: Path, *, key: bytes | None = None) -> None:
    fernet = Fernet(key or load_key())
    plaintext = source_db.read_bytes()
    destination.write_bytes(fernet.encrypt(plaintext))


def decrypt_backup(encrypted: Path, *, key: bytes | None = None) -> bytes:
    fernet = Fernet(key or load_key())
    try:
        return fernet.decrypt(encrypted.read_bytes())
    except InvalidToken as exc:
        raise ValueError("backup failed authentication") from exc
