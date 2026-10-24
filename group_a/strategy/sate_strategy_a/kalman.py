"""Kalman tick signal **A-SIG-01** (2.5σ innovation threshold)."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class KalmanSignal:
    innovation: float
    sigma: float
    direction: int
    triggered: bool


class KalmanTickFilter:
    def __init__(self, *, innovation_threshold_sigma: float = 2.5) -> None:
        self._threshold = innovation_threshold_sigma
        self._level = 0.0
        self._variance = 1.0
        self._initialized = False

    def update(self, price: float) -> KalmanSignal:
        if not self._initialized:
            self._level = price
            self._initialized = True
            return KalmanSignal(innovation=0.0, sigma=0.0, direction=0, triggered=False)
        innovation = price - self._level
        sigma = math.sqrt(max(self._variance, 1e-12))
        triggered = abs(innovation) > self._threshold * sigma
        direction = 0
        if triggered:
            direction = 1 if innovation > 0 else -1
        self._level += 0.2 * innovation
        self._variance = max(0.05, 0.9 * self._variance + 0.1 * innovation * innovation)
        return KalmanSignal(
            innovation=innovation,
            sigma=sigma,
            direction=direction,
            triggered=triggered,
        )
