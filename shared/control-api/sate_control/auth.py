"""Authenticated sessions with group-scoped authorisation (**A-P0-16**, **A-IND-02**)."""

from __future__ import annotations

from dataclasses import dataclass

from sate_control.scope import require_scope


@dataclass(frozen=True)
class Session:
    principal: str
    group_scope: str
    expires_at: str = ""

    def __post_init__(self) -> None:
        require_scope(self.group_scope)


def authorize_read(session: Session, scope: str) -> str:
    scope = require_scope(scope)
    if session.group_scope != scope:
        raise PermissionError(f"session {session.group_scope!r} cannot read {scope!r}")
    return scope


def authorize_control(session: Session, scope: str, *, allow_all_kill: bool = False) -> str:
    if allow_all_kill and scope == "ALL":
        return scope
    scope = require_scope(scope)
    if session.group_scope != scope:
        raise PermissionError(f"session {session.group_scope!r} cannot control {scope!r}")
    return scope
