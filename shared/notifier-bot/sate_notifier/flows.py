"""Scope + confirm flows (**TG-PO-06**, **TG-PO-07**)."""

from __future__ import annotations

import time

from sate_notifier.confirm import ConfirmError, confirm_label, sign_confirm, verify_confirm
from sate_notifier.control_client import submit_kill, submit_mode_sim
from sate_notifier.state_machine import BotState, SessionState

_CONFIRM_SECRET = b"sate-notifier-confirm-phase18"
_K1_TTL = 30
_K3_SECOND_TTL = 60


def begin_destructive(session: SessionState, action: str) -> dict[str, object]:
    session.reset()
    session.pending_action = action
    session.state = BotState.AWAITING_SCOPE
    session.expires_at = int(time.time()) + 60
    return {
        "state": session.state.value,
        "buttons": ["Group A", "Group B", "ALL", "Cancel"],
    }


def select_scope(session: SessionState, scope_label: str) -> dict[str, object]:
    if session.state != BotState.AWAITING_SCOPE:
        raise ValueError("no scope selection is pending")
    mapping = {"group a": "A", "group b": "B", "all": "ALL"}
    scope = mapping.get(scope_label.strip().lower())
    if scope is None:
        session.reset()
        return {"status": "cancelled"}
    session.pending_scope = scope
    session.state = BotState.AWAITING_CONFIRM
    session.expires_at = int(time.time()) + _K1_TTL
    action = session.pending_action
    token = sign_confirm(action=action, scope=scope, ttl_sec=_K1_TTL, secret=_CONFIRM_SECRET)
    label = confirm_label(action, scope)
    if action == "kill" and scope in {"A", "ALL"}:
        session.kill_step = 1
    return {"state": session.state.value, "confirm_label": label, "token": token}


def accept_confirm(session: SessionState, token: str) -> dict[str, object]:
    if session.state not in {BotState.AWAITING_CONFIRM, BotState.AWAITING_KILL2}:
        raise ValueError("no confirmation is pending")
    payload = verify_confirm(token, secret=_CONFIRM_SECRET)
    if payload.scope != session.pending_scope:
        raise ConfirmError("confirm scope mismatch")
    if session.state == BotState.AWAITING_KILL2 and payload.action == "kill_revoke":
        result = submit_kill(scope=session.pending_scope, kill_level="K3")
        session.reset()
        return {"status": "executed", "result": result}
    if payload.action != session.pending_action:
        raise ConfirmError("confirm scope mismatch")
    if session.pending_action == "kill" and session.kill_step == 1 and payload.action == "kill":
        session.state = BotState.AWAITING_KILL2
        session.kill_step = 2
        second = sign_confirm(
            action="kill_revoke",
            scope=payload.scope,
            ttl_sec=_K3_SECOND_TTL,
            secret=_CONFIRM_SECRET,
        )
        return {
            "status": "await_second_confirm",
            "confirm_label": f"Confirm KILL {payload.scope} — revokes credentials",
            "token": second,
        }
    if session.pending_action == "halt":
        result = submit_kill(scope=session.pending_scope, kill_level="K1")
        session.reset()
        return {"status": "executed", "result": result}
    if session.pending_action == "flatten":
        result = submit_kill(scope=session.pending_scope, kill_level="K2")
        session.reset()
        return {"status": "executed", "result": result}
    if session.pending_action == "mode_sim":
        result = submit_mode_sim(scope=session.pending_scope)
        session.reset()
        return {"status": "executed", "result": result}
    session.reset()
    raise ValueError("unknown pending action")


def scope_tag(scope: str, mode: str = "LIVE") -> str:
    if scope == "ALL":
        return "[ALL]"
    return f"[{scope}-{mode}]"
