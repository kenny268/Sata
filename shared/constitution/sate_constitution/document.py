"""Appendix A document, change class, and the LIVE gate owned by this artifact."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

import jsonschema

from sate_constitution.errors import ConstitutionError

_LOWER = (
    "risk.max_risk_per_trade_pct",
    "risk.max_open_notional_x_equity",
    "risk.max_daily_loss_pct",
    "risk.max_drawdown_pct",
    "risk.max_leverage_used",
    "risk.broker_balance_cap",
    "mode.ramp_factor",
)
_HIGHER = (
    "mode.arming_delay_hours",
    "mode.ramp_min_days",
    "mode.evidence_window_days",
    "capital.reference_floor",
    "capital.floor_warning_band_pct",
    "capital.floor_breach_sessions",
    "capital.reentry_block_days",
    "capital.ratify_cooloff_days",
    "treasury.cash_floor",
    "checkin.reminder_days",
    "checkin.manage_only_days",
    "checkin.flatten_days",
    "checkin.max_away_days",
)
_LOCK = ("meta.tighten_lock_hours", "meta.loosen_lock_hours")
_IGNORED = ("meta.version", "meta.signed_by")
_MODE = {"SIM": 0, "LIVE-L1": 1, "LIVE-L2": 2, "LIVE-L3": 3}
_FORBIDDEN = frozenset({
    "combined_equity",
    "combined_rcb",
    "portfolio_total",
    "trade_approval",
    "per_trade_approval",
})


def schema_path() -> Path:
    override = os.environ.get("SATE_CONSTITUTION_SCHEMA", "")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / "schemas" / "constitution.schema.json"


def canonical_bytes(document: dict[str, object]) -> bytes:
    return json.dumps(document, sort_keys=True, separators=(",", ":")).encode()


def validate_document(document: dict[str, object]) -> None:
    _reject_forbidden(document)
    envelope = {
        "constitution_id": document["meta"]["constitution_id"],
        "group_id": document["meta"]["group"],
        "version": document["meta"]["version"],
        "effective_at": "2026-01-01T00:00:00Z",
        "expires_at": "2027-01-01T00:00:00Z",
        "key_id": document["meta"]["signed_by"],
        "payload_hash": "0" * 64,
        "signature": "ab" * 64,
        "canonical": canonical_bytes(document).decode(),
        "document": document,
    }
    _validate_envelope(envelope)


def validate_envelope(envelope: dict[str, object]) -> None:
    _reject_forbidden(envelope.get("document", {}))
    _validate_envelope(envelope)
    document = envelope["document"]
    if not isinstance(document, dict):
        raise ConstitutionError("constitution document is missing", code="malformed")
    if envelope["version"] != document["meta"]["version"]:
        raise ConstitutionError("envelope version does not match the document", code="version")
    if envelope["group_id"] != document["meta"]["group"]:
        raise ConstitutionError("envelope group does not match the document", code="scope")
    if envelope["constitution_id"] != document["meta"]["constitution_id"]:
        raise ConstitutionError("constitution id does not match the document", code="malformed")
    canonical = canonical_bytes(document).decode()
    if envelope["canonical"] != canonical:
        raise ConstitutionError("canonical bytes do not match the document", code="signature")
    if envelope["expires_at"] <= envelope["effective_at"]:
        raise ConstitutionError("expiry is not after the effective time", code="expired")


def live_blockers(document: dict[str, object] | None) -> list[str]:
    """Gates this artifact owns. An empty list does not decide the rest of LIVE."""
    if document is None:
        return ["no_active_constitution"]
    blockers = []
    meta = document["meta"]
    if meta["tighten_lock_hours"] == 0 and meta["loosen_lock_hours"] == 0:
        blockers.append("time_lock_placeholder")
    if _decimal(document["risk"]["broker_balance_cap"]) == 0:
        blockers.append("broker_balance_cap_unset")
    if document["mode"]["state"] == "SIM":
        blockers.append("mode_is_sim")
    return blockers


def hours_are_placeholder(document: dict[str, object]) -> bool:
    meta = document["meta"]
    return meta["tighten_lock_hours"] == 0 and meta["loosen_lock_hours"] == 0


def lock_hours_are_ordered(document: dict[str, object]) -> bool:
    tighten = document["meta"]["tighten_lock_hours"]
    loosen = document["meta"]["loosen_lock_hours"]
    return tighten > 0 and loosen > tighten


def classify(before: dict[str, object], after: dict[str, object]) -> str:
    if after["meta"]["constitution_id"] != before["meta"]["constitution_id"]:
        raise ConstitutionError("a new version stays on the same constitution", code="version")
    if after["meta"]["group"] != before["meta"]["group"]:
        raise ConstitutionError("a new version stays in the same group", code="scope")
    if after["meta"]["version"] != before["meta"]["version"] + 1:
        raise ConstitutionError("version must be the next pin", code="version")
    flags: set[str] = set()
    old = _flatten(before)
    new = _flatten(after)
    paths = set(old) | set(new)
    lock_only = True
    for path in sorted(paths):
        if path in _IGNORED or old.get(path) == new.get(path):
            continue
        if path not in _LOCK:
            lock_only = False
        flags.add(_direction(path, old.get(path), new.get(path)))
    if not flags:
        raise ConstitutionError("proposal does not change the constitution", code="empty")
    if lock_only:
        if hours_are_placeholder(before):
            return "lock_hours"
        if "loosen" in flags:
            return "loosen"
        return "tighten"
    if "loosen" in flags:
        return "loosen"
    return "tighten"


def changed_paths(before: dict[str, object], after: dict[str, object]) -> tuple[str, ...]:
    old = _flatten(before)
    new = _flatten(after)
    paths = []
    for path in sorted(set(old) | set(new)):
        if path in _IGNORED:
            continue
        if old.get(path) != new.get(path):
            paths.append(path)
    return tuple(paths)


def window_open(envelope: dict[str, object], now: str) -> None:
    _stamp(now)
    effective = str(envelope["effective_at"])
    expires = str(envelope["expires_at"])
    _stamp(effective)
    _stamp(expires)
    if now < effective:
        raise ConstitutionError("constitution is not effective yet", code="not_yet_effective")
    if now >= expires:
        raise ConstitutionError("constitution has expired", code="expired")


def add_hours(stamp: str, hours: int) -> str:
    parsed = _stamp(stamp) + timedelta(hours=hours)
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_envelope(envelope: dict[str, object]) -> None:
    schema = json.loads(schema_path().read_text(encoding="utf-8"))
    try:
        jsonschema.validate(envelope, schema)
    except jsonschema.ValidationError as exc:
        raise ConstitutionError(f"constitution schema refused the artifact: {exc.message}", code="malformed") from exc


def _reject_forbidden(value: object) -> None:
    if isinstance(value, dict):
        overlap = _FORBIDDEN.intersection(value)
        if overlap:
            raise ConstitutionError(f"constitution cannot carry {sorted(overlap)}", code="forbidden")
        for item in value.values():
            _reject_forbidden(item)
    elif isinstance(value, list):
        for item in value:
            _reject_forbidden(item)


def _direction(path: str, before: object, after: object) -> str:
    if path == "mode.state":
        if _MODE[str(after)] > _MODE[str(before)]:
            return "loosen"
        return "tighten"
    if path == "risk.require_protective_stop":
        if after is True and before is False:
            return "tighten"
        return "loosen"
    if path in {"universe.LIVE-L1", "universe.LIVE-L2"}:
        added = set(after or ()) - set(before or ())
        if added:
            return "loosen"
        return "tighten"
    if path in _LOWER:
        if _decimal(after) < _decimal(before):
            return "tighten"
        return "loosen"
    if path in _HIGHER or path in _LOCK:
        if _decimal(after) > _decimal(before):
            return "tighten"
        return "loosen"
    return "loosen"


def _flatten(value: object, prefix: str = "") -> dict[str, object]:
    if isinstance(value, dict):
        flat: dict[str, object] = {}
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            flat.update(_flatten(item, path))
        return flat
    if isinstance(value, list):
        return {prefix: tuple(value)}
    return {prefix: value}


def _decimal(value: object) -> Decimal:
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise ConstitutionError("numeric constitution fields must be decimal", code="malformed") from exc
    return amount


def _stamp(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ConstitutionError("timestamp must be UTC", code="malformed")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ConstitutionError("timestamp must be UTC", code="malformed") from exc
    return parsed.replace(tzinfo=timezone.utc)
