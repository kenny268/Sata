"""§16.1 verification matrix registry."""

from __future__ import annotations

import json
import os
from pathlib import Path

_MATRIX = (
    Path(__file__).resolve().parents[3] / "shared" / "ci" / "verification-matrix.json"
)


def load_matrix() -> dict[str, object]:
    return json.loads(_MATRIX.read_text(encoding="utf-8"))


def matrix_evidence_present(root: Path | None = None) -> bool:
    base = root or Path(__file__).resolve().parents[3]
    data = load_matrix()
    classes = data.get("classes", {})
    if not isinstance(classes, dict):
        return False
    for paths in classes.values():
        if not isinstance(paths, list):
            return False
        for rel in paths:
            if not (base / str(rel)).is_file():
                return False
    return True


def matrix_green(*, env_override: bool | None = None) -> bool:
    if env_override is not None:
        return env_override
    if os.environ.get("SATE_VERIFICATION_MATRIX_GREEN", "").lower() in {"1", "true", "yes"}:
        return True
    return matrix_evidence_present()
