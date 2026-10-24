"""Copy encrypted backup off-host (**§14.2**)."""

from __future__ import annotations

import shutil
from pathlib import Path


def copy_off_host(encrypted_backup: Path, remote_dir: Path) -> Path:
    if not encrypted_backup.is_file():
        raise FileNotFoundError("encrypted backup missing")
    remote_dir.mkdir(parents=True, exist_ok=True)
    destination = remote_dir / encrypted_backup.name
    shutil.copy2(encrypted_backup, destination)
    return destination
