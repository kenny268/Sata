"""Decision log blockers **A-DEC-01**, **A-DEC-08**, **A-DEC-10**."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

BlockerStatus = Literal["OPEN", "BLOCKED", "RESOLVED"]

PHASE24_BLOCKERS = ("A-DEC-01", "A-DEC-08", "A-DEC-10")


@dataclass(frozen=True)
class BlockerRecord:
    decision_id: str
    status: BlockerStatus
    note: str = ""


def default_blockers() -> tuple[BlockerRecord, ...]:
    return tuple(
        BlockerRecord(decision_id=item, status="OPEN", note="decision-log default")
        for item in PHASE24_BLOCKERS
    )


def blockers_allow_live_arm(blockers: tuple[BlockerRecord, ...]) -> bool:
    for item in blockers:
        if item.status == "OPEN":
            return False
        if item.decision_id == "A-DEC-10" and item.status == "BLOCKED":
            return False
    return True


def open_blocker_ids(blockers: tuple[BlockerRecord, ...]) -> list[str]:
    return [item.decision_id for item in blockers if item.status == "OPEN"]
