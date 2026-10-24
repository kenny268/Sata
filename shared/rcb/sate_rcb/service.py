"""Ratified capital base. Increases wait out a clean cool-off and a passkey."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation

from sate_rcb.errors import RcbError

SCOPES = frozenset({"A", "B"})
HALT_LEVELS = frozenset({"L1", "L2", "L3", "L4"})
SEVERE_HALTS = frozenset({"L2", "L3", "L4"})
COOL_OFF_DAYS = 14
# Reference floors from the system overview. They are not L2 or L3 rungs.
REFERENCE_FLOOR = {"A": Decimal(500), "B": Decimal(200)}
_FORBIDDEN = frozenset({
    "combined_equity",
    "combined_rcb",
    "portfolio_total",
    "withdrawable",
    "withdrawable_cash",
    "cash",
})
_ZERO = Decimal(0)
_WRITER = "rcb"


@dataclass(frozen=True)
class RcbState:
    group_scope: str
    ratified_base: str | None
    version: int
    proposed_base: str | None
    clean_since: str | None
    halt_level: str | None
    injections_paused: bool
    last_deposit_effect: str
    seq: int


def blank(scope: str) -> RcbState:
    if scope not in SCOPES:
        raise RcbError(f"RCB refuses scope {scope!r}")
    return RcbState(
        group_scope=scope,
        ratified_base=None,
        version=0,
        proposed_base=None,
        clean_since=None,
        halt_level=None,
        injections_paused=False,
        last_deposit_effect="",
        seq=0,
    )


def effective_limit(state: RcbState, equity: str) -> str:
    """A-RCB-01 and A-RCB-02. Equity below the base shrinks the limit now."""
    if state.group_scope not in SCOPES:
        raise RcbError(f"RCB refuses scope {state.group_scope!r}")
    if state.ratified_base is None:
        return "0"
    base = _dec(state.ratified_base)
    marked = _money(equity)
    return _text(min(base, marked))


def floor_met(state: RcbState) -> bool:
    """CT-A1. The reference floor is compared with the ratified base, not equity."""
    if state.ratified_base is None:
        return False
    return _dec(state.ratified_base) >= REFERENCE_FLOOR[state.group_scope]


def verdict_inputs(state: RcbState, equity: str) -> dict[str, object]:
    """Inputs the kernel consumes. Version 0 is not a verdict input."""
    if state.version < 1 or state.ratified_base is None:
        raise RcbError("kernel verdict requires an RCB version")
    return {
        "group_scope": state.group_scope,
        "rcb_version": state.version,
        "effective_limit": effective_limit(state, equity),
    }


def export_state(state: RcbState) -> dict[str, object]:
    return {
        "group_scope": state.group_scope,
        "ratified_base": state.ratified_base,
        "version": state.version,
        "proposed_base": state.proposed_base,
        "clean_since": state.clean_since,
        "halt_level": state.halt_level,
        "injections_paused": state.injections_paused,
        "last_deposit_effect": state.last_deposit_effect,
        "read_only": True,
    }


def project(scope: str, records: list) -> RcbState:
    state = blank(scope)
    for record in sorted(records, key=lambda item: item.seq):
        state = fold(state, record)
    return state


def fold(state: RcbState, record) -> RcbState:
    if record.seq <= state.seq:
        return state
    if record.group_scope == "GLOBAL":
        if record.event_type == "rcb_change":
            raise RcbError("RCB cannot use a pooled scope", code="pooled")
        return replace(state, seq=record.seq)
    if record.group_scope != state.group_scope:
        return replace(state, seq=record.seq)
    if record.event_type == "halt":
        return _halt_fact(state, record)
    if record.event_type != "rcb_change":
        return replace(state, seq=record.seq)
    if record.writer_id != _WRITER:
        raise RcbError("RCB changes are written by the RCB service", code="writer")
    return apply_event(state, record.payload, record.seq)


def apply_event(state: RcbState, payload: dict[str, object], seq: int) -> RcbState:
    overlap = _FORBIDDEN.intersection(payload)
    if overlap:
        raise RcbError(f"RCB payload cannot carry {sorted(overlap)}")
    foreign = payload.get("group_id")
    if foreign is not None and foreign != state.group_scope:
        raise RcbError("RCB event group does not match the service scope")
    kind = str(payload.get("kind", ""))
    if kind == "bind":
        return _bind(state, payload, seq)
    if kind == "deposit":
        return _deposit(state, payload, seq)
    if kind == "propose":
        return _propose(state, payload, seq)
    if kind == "halt":
        return _halt(state, payload, seq)
    if kind == "halt_clear":
        return replace(state, halt_level=None, injections_paused=False, seq=seq)
    if kind == "withdrawal":
        return _withdraw(state, payload, seq)
    if kind == "ratify":
        return _ratify(state, payload, seq)
    raise RcbError(f"unknown RCB kind {kind!r}")


def _bind(state: RcbState, payload: dict[str, object], seq: int) -> RcbState:
    if state.ratified_base is not None:
        raise RcbError("base is already bound")
    _assertion(payload)
    base = _text(_money(payload.get("ratified_base")))
    if _dec(base) <= _ZERO:
        raise RcbError("ratified base must be positive")
    return replace(state, ratified_base=base, version=1, seq=seq)


def _deposit(state: RcbState, payload: dict[str, object], seq: int) -> RcbState:
    amount = _money(payload.get("amount"))
    if amount <= _ZERO:
        raise RcbError("deposit must be positive")
    occurred = _occurred(payload)
    if state.halt_level is not None or state.injections_paused:
        return replace(state, last_deposit_effect="inert_halt", seq=seq)
    if state.ratified_base is None:
        raise RcbError("bind a base before recording a deposit")
    return _queue(state, _dec(state.ratified_base) + amount, occurred, seq)


def _propose(state: RcbState, payload: dict[str, object], seq: int) -> RcbState:
    proposed = _money(payload.get("new_base"))
    occurred = _occurred(payload)
    if state.halt_level is not None or state.injections_paused:
        return replace(state, last_deposit_effect="inert_halt", seq=seq)
    if state.ratified_base is None:
        raise RcbError("bind a base before proposing an increase")
    if proposed <= _dec(state.ratified_base):
        raise RcbError("proposal is not an increase")
    return _queue(state, proposed, occurred, seq)


def _queue(state: RcbState, proposed: Decimal, occurred: str, seq: int) -> RcbState:
    if state.proposed_base is not None:
        proposed = max(proposed, _dec(state.proposed_base))
    clean = state.clean_since or occurred
    return replace(
        state,
        proposed_base=_text(proposed),
        clean_since=clean,
        last_deposit_effect="pending_ratification",
        seq=seq,
    )


def _halt_fact(state: RcbState, record) -> RcbState:
    payload = dict(record.payload)
    overlap = _FORBIDDEN.intersection(payload)
    if overlap:
        raise RcbError(f"RCB payload cannot carry {sorted(overlap)}", code="forbidden_field")
    if "occurred_at" not in payload:
        payload["occurred_at"] = record.occurred_at
    return _halt(state, payload, record.seq)


def _halt(state: RcbState, payload: dict[str, object], seq: int) -> RcbState:
    level = str(payload.get("level", ""))
    if level not in HALT_LEVELS:
        raise RcbError(f"unknown halt level {level!r}")
    occurred = _occurred(payload)
    if level in SEVERE_HALTS:
        return replace(
            state,
            halt_level=level,
            injections_paused=True,
            clean_since=occurred,
            seq=seq,
        )
    return replace(state, halt_level=level, seq=seq)


def _withdraw(state: RcbState, payload: dict[str, object], seq: int) -> RcbState:
    if state.ratified_base is None:
        raise RcbError("there is no ratified base to reduce")
    amount = _money(payload.get("amount"))
    _money(payload.get("fee"))
    _money(payload.get("fx_cost"))
    if amount <= _ZERO:
        raise RcbError("withdrawal must be positive")
    if amount > _dec(state.ratified_base):
        raise RcbError("withdrawal exceeds the ratified base")
    return replace(
        state,
        ratified_base=_text(_dec(state.ratified_base) - amount),
        version=state.version + 1,
        seq=seq,
    )


def _ratify(state: RcbState, payload: dict[str, object], seq: int) -> RcbState:
    _assertion(payload)
    if state.injections_paused or state.halt_level in SEVERE_HALTS:
        raise RcbError("injections are paused", code="injections_paused")
    if state.proposed_base is None or state.ratified_base is None or state.clean_since is None:
        raise RcbError("nothing to ratify", code="nothing_to_ratify")
    if payload.get("previous_base") != state.ratified_base:
        raise RcbError("ratification does not match the current base", code="mismatch")
    if payload.get("new_base") != state.proposed_base:
        raise RcbError("ratification does not match the proposal", code="mismatch")
    if payload.get("clean_since") != state.clean_since:
        raise RcbError("ratification does not match the cool-off", code="mismatch")
    ratified_at = payload.get("ratified_at")
    if not _cool_off_complete(state.clean_since, ratified_at):
        raise RcbError("cool-off has not finished", code="cool_off_incomplete")
    return replace(
        state,
        ratified_base=state.proposed_base,
        proposed_base=None,
        version=state.version + 1,
        seq=seq,
    )


def _assertion(payload: dict[str, object]) -> None:
    value = payload.get("passkey_assertion")
    if not isinstance(value, str) or not value.strip():
        raise RcbError("passkey assertion is required", code="passkey_required")


def _occurred(payload: dict[str, object]) -> str:
    value = payload.get("occurred_at")
    _stamp(value)
    return str(value)


def _cool_off_complete(start: str, end: object) -> bool:
    if not isinstance(end, str):
        return False
    return _stamp(end) - _stamp(start) >= timedelta(days=COOL_OFF_DAYS)


def _stamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise RcbError("timestamp must be UTC")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise RcbError("timestamp must be UTC") from exc
    return parsed.replace(tzinfo=UTC)


def _money(value: object) -> Decimal:
    if not isinstance(value, str) or not value.strip():
        raise RcbError("money values must be decimal strings")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise RcbError("money values must be decimal strings") from exc
    if not amount.is_finite():
        raise RcbError("money values must be finite")
    return amount


def _dec(value: str) -> Decimal:
    return Decimal(value)


def _text(amount: Decimal) -> str:
    text = format(amount, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
