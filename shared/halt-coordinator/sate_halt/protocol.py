"""Global halt states (**§9.3**, **INV-06**)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HaltState(str, Enum):
    HALT_REQUESTED = "HALT_REQUESTED"
    HALT_CONFIRMED_A = "HALT_CONFIRMED_A"
    HALT_CONFIRMED_B = "HALT_CONFIRMED_B"
    HALT_CONFIRMED_ALL = "HALT_CONFIRMED_ALL"


@dataclass
class Protocol:
    command_id: str
    scope: str
    kill_level: str
    reason: str
    channel: str
    identity: str
    confirmed_a: bool = False
    confirmed_b: bool = False
    b_reachable: bool = False

    def status(self) -> HaltState:
        if self.scope == "A":
            return HaltState.HALT_CONFIRMED_A if self.confirmed_a else HaltState.HALT_REQUESTED
        if self.scope == "B":
            if not self.b_reachable:
                return HaltState.HALT_REQUESTED
            return HaltState.HALT_CONFIRMED_B if self.confirmed_b else HaltState.HALT_REQUESTED
        if self.scope != "ALL":
            raise ValueError("explicit group scope required")
        if self.confirmed_a and self.confirmed_b:
            return HaltState.HALT_CONFIRMED_ALL
        if self.confirmed_a and not self.b_reachable:
            return HaltState.HALT_CONFIRMED_A
        return HaltState.HALT_REQUESTED
