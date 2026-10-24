"""Calibration table **A-COG-02**."""

from __future__ import annotations

from dataclasses import dataclass, field

C_MAX_START = 0.3
Q_MAX = 1.0


@dataclass
class CalibrationTable:
    version: str = "shadow-v1"
    cap: float = C_MAX_START
    samples: int = 0

    def apply(self, raw_c: float) -> float:
        if self.samples < 30:
            return min(raw_c, self.cap)
        return min(raw_c, 1.0)

    def apply_q(self, raw_q: float) -> float:
        bounded = max(-Q_MAX, min(Q_MAX, raw_q))
        return bounded


@dataclass
class CalibrationRegistry:
    tables: dict[str, CalibrationTable] = field(default_factory=dict)

    def get(self, version: str) -> CalibrationTable:
        return self.tables.get(version, CalibrationTable(version=version))
