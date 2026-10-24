"""Backup job with last success/failure observability."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from sate_backup.snapshot import create_encrypted_backup


@dataclass
class BackupJob:
    source_db: Path
    destination: Path
    key: bytes
    last_success: str | None = None
    last_failure: str | None = None
    attempts: list[str] = field(default_factory=list)

    def run(self, *, at: str) -> None:
        self.attempts.append(at)
        try:
            create_encrypted_backup(self.source_db, self.destination, key=self.key)
            self.last_success = at
            self.last_failure = None
        except (OSError, ValueError) as exc:
            self.last_failure = f"{at}:{exc}"

    def metric(self) -> dict[str, object]:
        return {
            "group_scope": "A",
            "backup_last_success": self.last_success,
            "backup_last_failure": self.last_failure,
            "attempts": len(self.attempts),
        }
