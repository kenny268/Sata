"""Metric envelope with mandatory group scope (**§14.1**)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricSample:
    name: str
    value: float
    group_scope: str
    observed_at: str


def sample(name: str, value: float, *, group_scope: str, observed_at: str) -> MetricSample:
    if group_scope not in {"A", "GLOBAL"}:
        raise ValueError("group_scope must be A or GLOBAL for Group A monitoring")
    return MetricSample(name=name, value=value, group_scope=group_scope, observed_at=observed_at)
