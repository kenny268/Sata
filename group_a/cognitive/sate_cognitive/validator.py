"""Validator outcomes (**§11.3**)."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from sate_cognitive.injection import evidence_is_safe

_SCHEMA = json.loads(
    (Path(__file__).resolve().parents[3] / "shared" / "schemas" / "advisory-signal.schema.json").read_text(
        encoding="utf-8"
    )
)


def validate_schema(signal: dict[str, object]) -> None:
    jsonschema.validate(signal, _SCHEMA)


def validate_evidence_refs(signal: dict[str, object]) -> str | None:
    refs = signal.get("evidence_refs")
    if not isinstance(refs, list):
        return "malformed_schema"
    for item in refs:
        if not isinstance(item, str) or not evidence_is_safe(item):
            return "injection_or_malformed"
    return None


def is_within_ttl(*, valid_from: str, valid_until: str, now: str) -> bool:
    return valid_from <= now <= valid_until
