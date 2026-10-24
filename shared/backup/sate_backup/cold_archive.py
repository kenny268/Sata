"""Cold archive with reconstruct manifest (**A-LOG-04**)."""

from __future__ import annotations

import gzip
import json
from pathlib import Path


def archive_fact_log(source_db: Path, destination_gz: Path, *, chain_head: str, decision_ref: str) -> None:
    payload = source_db.read_bytes()
    destination_gz.write_bytes(gzip.compress(payload))
    manifest = destination_gz.with_suffix(".manifest.json")
    manifest.write_text(
        json.dumps(
            {
                "schema": "sate-cold-archive/v1",
                "source": source_db.name,
                "chain_head": chain_head,
                "decision_docs_by_reference": decision_ref,
                "compressed": destination_gz.name,
            },
            sort_keys=True,
            indent=2,
        ),
        encoding="utf-8",
    )


def reconstruct_path(manifest_path: Path) -> Path:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    gz = manifest_path.parent / str(data["compressed"])
    if not gz.is_file():
        raise FileNotFoundError("compressed archive missing")
    return gz
