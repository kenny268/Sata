"""**A-DEC-04**, **A-DEC-09** LIVE resolution checks."""

from __future__ import annotations

import json
from pathlib import Path

from sate_backup.rpo_rto import load_register, merge_deploy_overrides, validate_register

try:
    from sate_constitution.document import hours_are_placeholder, lock_hours_are_ordered
except ImportError:  # pragma: no cover
    hours_are_placeholder = None  # type: ignore[misc, assignment]
    lock_hours_are_ordered = None  # type: ignore[misc, assignment

_RPO_RTO = Path(__file__).resolve().parents[3] / "shared" / "ci" / "a-dec-09-rpo-rto.json"


def a_dec_04_reasons(constitution: dict[str, object] | None) -> list[str]:
    if constitution is None:
        return ["a_dec_04_constitution_missing"]
    if hours_are_placeholder is None:
        return ["a_dec_04_constitution_module_missing"]
    if hours_are_placeholder(constitution):
        return ["a_dec_04_time_lock_open"]
    if not lock_hours_are_ordered(constitution):
        return ["a_dec_04_lock_hours_invalid"]
    return []


def a_dec_09_reasons() -> list[str]:
    data = merge_deploy_overrides(load_register(_RPO_RTO))
    summary = validate_register(data)
    if summary["live_gate_blocked_until_set"]:
        return ["a_dec_09_rpo_rto_unset"]
    return []


def load_cg_live_record() -> dict[str, object]:
    path = Path(__file__).resolve().parents[3] / "shared" / "ci" / "cg-live-record.json"
    return json.loads(path.read_text(encoding="utf-8"))
