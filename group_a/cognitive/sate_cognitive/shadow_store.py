"""Persist shadow accumulator between SIM runs and weekly export."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from sate_cognitive.shadow import ShadowAccumulator, ShadowSample


def save_accumulator(acc: ShadowAccumulator, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "week": acc.week,
        "ingested": acc.ingested,
        "abstains": acc.abstains,
        "samples": [asdict(sample) for sample in acc.samples],
    }
    path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")


def load_accumulator(path: Path) -> ShadowAccumulator:
    raw = json.loads(path.read_text(encoding="utf-8"))
    acc = ShadowAccumulator(week=str(raw["week"]))
    acc.ingested = int(raw["ingested"])
    acc.abstains = int(raw["abstains"])
    acc.samples = [
        ShadowSample(
            signal_id=str(item["signal_id"]),
            shadow_q=float(item["shadow_q"]),
            outcome=float(item["outcome"]),
        )
        for item in raw.get("samples", [])
    ]
    return acc
