"""Bot conversational state (**§10**)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class BotState(str, Enum):
    READY = "READY"
    AWAITING_SCOPE = "AWAITING_SCOPE"
    AWAITING_CONFIRM = "AWAITING_CONFIRM"
    AWAITING_KILL2 = "AWAITING_KILL2"


@dataclass
class SessionState:
    state: BotState = BotState.READY
    pending_action: str = ""
    pending_scope: str = ""
    kill_step: int = 0
    expires_at: int = 0

    def reset(self) -> None:
        self.state = BotState.READY
        self.pending_action = ""
        self.pending_scope = ""
        self.kill_step = 0
        self.expires_at = 0


@dataclass
class StateStore:
    sessions: dict[str, SessionState] = field(default_factory=dict)

    def for_user(self, user_id: str) -> SessionState:
        return self.sessions.setdefault(user_id, SessionState())
