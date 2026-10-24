"""AdvisorySignal ingestion → zero view when invalid (**A-COG-01**)."""

from __future__ import annotations

from dataclasses import dataclass

import jsonschema

from sate_cognitive.calibration import CalibrationRegistry
from sate_cognitive.gate import trading_advisory_multiplier
from sate_cognitive.signing import verify_signature
from sate_cognitive.validator import is_within_ttl, validate_evidence_refs, validate_schema


@dataclass(frozen=True)
class IngestResult:
    ok: bool
    shadow_q: float
    shadow_c: float
    trading_view: float | None
    reason: str = ""


def ingest_signal(
    signal: dict[str, object],
    *,
    now: str,
    public_key: bytes,
    registry: CalibrationRegistry | None = None,
    account_mode: str = "SIM",
) -> IngestResult:
    tables = registry or CalibrationRegistry()
    try:
        validate_schema(signal)
    except (jsonschema.ValidationError, ValueError, TypeError):
        return IngestResult(ok=False, shadow_q=0.0, shadow_c=0.0, trading_view=None, reason="malformed_schema")
    if not verify_signature(signal, public_key=public_key):
        return IngestResult(ok=False, shadow_q=0.0, shadow_c=0.0, trading_view=None, reason="invalid_signature")
    evidence_error = validate_evidence_refs(signal)
    if evidence_error is not None:
        return IngestResult(ok=False, shadow_q=0.0, shadow_c=0.0, trading_view=None, reason=evidence_error)
    if not is_within_ttl(
        valid_from=str(signal["valid_from"]),
        valid_until=str(signal["valid_until"]),
        now=now,
    ):
        return IngestResult(ok=False, shadow_q=0.0, shadow_c=0.0, trading_view=None, reason="expired")
    if str(signal["state"]) == "ABSTAIN":
        return IngestResult(ok=False, shadow_q=0.0, shadow_c=0.0, trading_view=None, reason="abstain")
    table = tables.get(str(signal["calibration_version"]))
    q = table.apply_q(float(signal["q"]))
    c = table.apply(float(signal["c"]))
    multiplier = trading_advisory_multiplier(account_mode=account_mode)
    trading_view = None if multiplier == 0.0 else q * multiplier
    return IngestResult(ok=True, shadow_q=q, shadow_c=c, trading_view=trading_view, reason="active")
