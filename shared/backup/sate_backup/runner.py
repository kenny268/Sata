"""Scheduled backup runner (cron / compose sidecar)."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from sate_backup.job import BackupJob
from sate_backup.off_host import copy_off_host
from sate_backup.snapshot import load_key


def run_scheduled_backup() -> dict[str, object]:
    source = Path(os.environ.get("SATE_FACTLOG_DB", "")).expanduser()
    if not source.is_file():
        raise FileNotFoundError("SATE_FACTLOG_DB must point at the fact log database")
    backup_dir = Path(os.environ.get("SATE_BACKUP_DIR", "/data/backups"))
    backup_dir.mkdir(parents=True, exist_ok=True)
    destination = backup_dir / "factlog.db.enc"
    key = load_key()
    at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    job = BackupJob(source_db=source, destination=destination, key=key)
    job.run(at=at)
    remote = os.environ.get("SATE_BACKUP_REMOTE_DIR", "").strip()
    off_host_path = None
    if remote:
        off_host_path = str(copy_off_host(destination, Path(remote)))
    metric = job.metric()
    metric["off_host_path"] = off_host_path
    return metric


def main() -> None:
    result = run_scheduled_backup()
    if result.get("backup_last_failure"):
        raise SystemExit(str(result["backup_last_failure"]))
    print("backup runner ok", result.get("backup_last_success"))


if __name__ == "__main__":
    main()
