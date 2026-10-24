"""SEC-01 allowlist gate."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Allowlist:
    chat_id: str
    user_id: str

    def authorized(self, *, chat_id: str, user_id: str) -> bool:
        return chat_id == self.chat_id and user_id == self.user_id
