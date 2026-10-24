"""**A-DEC-09** RPO/RTO harness — values owner-set; schema enforced when present."""

from __future__ import annotations

import json
import os
from pathlib import Path


def load_register(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def merge_deploy_overrides(data: dict[str, object]) -> dict[str, object]:
    """Apply owner RPO/RTO from deploy env without committing numbers to git."""
    merged = dict(data)
    rpo = os.environ.get("SATE_RPO_MINUTES", "").strip()
    rto = os.environ.get("SATE_RTO_MINUTES", "").strip()
    if rpo.isdigit():
        merged["rpo_minutes"] = int(rpo)
    if rto.isdigit():
        merged["rto_minutes"] = int(rto)
    if merged.get("rpo_minutes") is not None and merged.get("rto_minutes") is not None:
        merged["live_gate_blocked_until_set"] = False
    return merged


def validate_register(data: dict[str, object]) -> dict[str, object]:
    rpo = data.get("rpo_minutes")
    rto = data.get("rto_minutes")
    owner_set = rpo is not None and rto is not None
    if owner_set:
        if not isinstance(rpo, int) or rpo <= 0:
            raise ValueError("rpo_minutes must be a positive integer when set")
        if not isinstance(rto, int) or rto <= 0:
            raise ValueError("rto_minutes must be a positive integer when set")
    return {
        "decision": str(data.get("decision", "")),
        "owner_set": owner_set,
        "live_gate_blocked_until_set": bool(data.get("live_gate_blocked_until_set", True)),
    }
