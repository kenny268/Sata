"""Emergency relay policy (**A-DEC-08**, **SEC**)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RelayPolicy:
    enabled: bool
    endpoint: str = ""
    auth_method: str = ""
    replay_policy: str = ""

    def sec_ok(self) -> bool:
        if not self.enabled:
            return True
        return bool(self.endpoint and self.auth_method and self.replay_policy)


def relay_policy_from_env() -> RelayPolicy:
    enabled = os.environ.get("SATE_SEC_RELAY_ENABLED", "").lower() in {"1", "true", "yes"}
    return RelayPolicy(
        enabled=enabled,
        endpoint=os.environ.get("SATE_SEC_RELAY_ENDPOINT", ""),
        auth_method=os.environ.get("SATE_SEC_RELAY_AUTH", ""),
        replay_policy=os.environ.get("SATE_SEC_RELAY_REPLAY", ""),
    )
