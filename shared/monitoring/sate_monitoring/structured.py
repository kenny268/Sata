"""Structured log and trace envelopes for metrics integration."""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class ObservationRecord:
    trace_id: str
    component: str
    event: str
    group_scope: str
    fields: dict[str, object]


def emit(component: str, event: str, *, group_scope: str, **fields: object) -> ObservationRecord:
    return ObservationRecord(
        trace_id=uuid.uuid4().hex,
        component=component,
        event=event,
        group_scope=group_scope,
        fields=fields,
    )
