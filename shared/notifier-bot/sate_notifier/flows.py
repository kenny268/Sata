"""Scope + confirm flows (**TG-PO-06**, **TG-PO-07**).

Confirm buttons are signed with a caller-supplied secret. An empty secret fails closed.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from sate_notifier.confirm import ConfirmError, confirm_label, sign_confirm, verify_confirm
from sate_notifier.control_client import submit_kill, submit_mode_sim
from sate_notifier.state_machine import BotState, SessionState
from sate_notifier.tags import scope_tag

_K1_TTL = 30
_SCOPE_TTL = 60
_K3_SECOND_TTL = 60

Dispatch = Callable[[dict[str, object]], dict[str, object]]


def begin_destructive(session: SessionState, action: str, *, now: int | None = None) -> dict[str, object]:
    moment = _now(now)
    session.reset()
    session.pending_action = action
    session.state = BotState.AWAITING_SCOPE
    session.expires_at = moment + _SCOPE_TTL
    return {
        "state": session.state.value,
        "buttons": ["Group A", "Group B", "ALL", "Cancel"],
    }


def begin_mode_sim(session: SessionState, *, secret: bytes, now: int | None = None) -> dict[str, object]:
    """LIVE to SIM is reduce-only. Flatten is a second signed button, not a default."""
    if not secret:
        raise ConfirmError("confirm secret unset")
    moment = _now(now)
    session.reset()
    session.pending_action = "mode_sim"
    session.pending_scope = "A"
    session.state = BotState.AWAITING_CONFIRM
    session.expires_at = moment + _K1_TTL
    session.issued_token = sign_confirm(
        action="mode_sim", scope="A", ttl_sec=_K1_TTL, secret=secret, now=moment
    )
    session.pending_label = "Switch A to SIM"
    session.alt_token = sign_confirm(
        action="mode_sim_flatten", scope="A", ttl_sec=_K1_TTL, secret=secret, now=moment
    )
    session.alt_label = "Switch A + Flatten"
    return {
        "state": session.state.value,
        "buttons": [session.pending_label, session.alt_label, "Cancel"],
        "confirm_label": session.pending_label,
        "token": session.issued_token,
        "alt_token": session.alt_token,
    }


def begin_cancel_arm(session: SessionState, *, secret: bytes, now: int | None = None) -> dict[str, object]:
    if not secret:
        raise ConfirmError("confirm secret unset")
    moment = _now(now)
    session.reset()
    session.pending_action = "cancel_arm"
    session.pending_scope = "A"
    session.state = BotState.AWAITING_CONFIRM
    session.expires_at = moment + _K1_TTL
    session.issued_token = sign_confirm(
        action="cancel_arm", scope="A", ttl_sec=_K1_TTL, secret=secret, now=moment
    )
    session.pending_label = "Confirm cancel arming A"
    return {
        "state": session.state.value,
        "confirm_label": session.pending_label,
        "token": session.issued_token,
        "buttons": [session.pending_label, "Cancel"],
    }


def select_scope(
    session: SessionState,
    scope_label: str,
    *,
    secret: bytes,
    now: int | None = None,
    position_count: str = "unknown",
) -> dict[str, object]:
    moment = _now(now)
    _require_open(session, BotState.AWAITING_SCOPE, moment)
    if not secret:
        session.reset()
        raise ConfirmError("confirm secret unset")
    mapping = {"group a": "A", "group b": "B", "all": "ALL"}
    scope = mapping.get(scope_label.strip().lower())
    if scope is None:
        session.reset()
        return {"status": "cancelled"}
    session.pending_scope = scope
    session.state = BotState.AWAITING_CONFIRM
    session.expires_at = moment + _K1_TTL
    action = session.pending_action
    token = sign_confirm(action=action, scope=scope, ttl_sec=_K1_TTL, secret=secret, now=moment)
    label = confirm_label(action, scope)
    session.issued_token = token
    session.pending_label = label
    if action == "kill" and scope in {"A", "B", "ALL"}:
        session.kill_step = 1
    detail = ""
    if action == "flatten":
        detail = f"Positions: {position_count}"
    return {
        "state": session.state.value,
        "confirm_label": label,
        "token": token,
        "detail": detail,
        "scope": scope,
        "scope_tag": scope_tag(scope),
    }


def accept_confirm(
    session: SessionState,
    token: str,
    *,
    secret: bytes,
    now: int | None = None,
    dispatch: Dispatch | None = None,
) -> dict[str, object]:
    moment = _now(now)
    if session.state not in {BotState.AWAITING_CONFIRM, BotState.AWAITING_KILL2}:
        raise ValueError("no confirmation is pending")
    if not secret:
        session.reset()
        raise ConfirmError("confirm secret unset")
    if session.expires_at and moment > session.expires_at:
        session.reset()
        raise ConfirmError("confirm token expired")
    try:
        payload = verify_confirm(token, secret=secret, now=moment)
    except ConfirmError:
        session.reset()
        raise
    if payload.scope != session.pending_scope:
        session.reset()
        raise ConfirmError("confirm scope mismatch")
    if session.state == BotState.AWAITING_KILL2 and payload.action == "kill_revoke":
        result = submit_kill(scope=session.pending_scope, kill_level="K3", dispatch=dispatch)
        session.reset()
        return _done(result)
    if payload.action not in {session.pending_action, "mode_sim_flatten"}:
        session.reset()
        raise ConfirmError("confirm scope mismatch")
    if session.pending_action == "kill" and session.kill_step == 1 and payload.action == "kill":
        session.state = BotState.AWAITING_KILL2
        session.kill_step = 2
        session.expires_at = moment + _K3_SECOND_TTL
        second = sign_confirm(
            action="kill_revoke",
            scope=payload.scope,
            ttl_sec=_K3_SECOND_TTL,
            secret=secret,
            now=moment,
        )
        label = f"Confirm KILL {payload.scope} — revokes credentials"
        session.issued_token = second
        session.pending_label = label
        return {"status": "await_second_confirm", "confirm_label": label, "token": second}
    if session.pending_action == "halt" and payload.action == "halt":
        result = submit_kill(scope=session.pending_scope, kill_level="K1", dispatch=dispatch)
        session.reset()
        return _done(result)
    if session.pending_action == "flatten" and payload.action == "flatten":
        result = submit_kill(scope=session.pending_scope, kill_level="K2", dispatch=dispatch)
        session.reset()
        return _done(result)
    if payload.action == "mode_sim":
        result = submit_mode_sim(scope=session.pending_scope, flatten=False, dispatch=dispatch)
        session.reset()
        return _done(result)
    if payload.action == "mode_sim_flatten":
        result = submit_mode_sim(scope=session.pending_scope, flatten=True, dispatch=dispatch)
        session.reset()
        return _done(result)
    if payload.action == "cancel_arm":
        result = submit_mode_sim(scope="A", flatten=False, dispatch=dispatch, action="cancel_arm")
        session.reset()
        return _done(result)
    session.reset()
    raise ValueError("unknown pending action")


def _done(result: dict[str, object]) -> dict[str, object]:
    status = "executed" if result.get("issued") == "true" else "validated"
    return {"status": status, "result": result}


def _require_open(session: SessionState, expected: BotState, moment: int) -> None:
    if session.state != expected:
        raise ValueError("no scope selection is pending")
    if session.expires_at and moment > session.expires_at:
        session.reset()
        raise ConfirmError("confirm token expired")


def _now(now: int | None) -> int:
    return int(time.time()) if now is None else now
