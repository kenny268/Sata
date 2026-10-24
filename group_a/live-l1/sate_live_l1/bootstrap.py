"""Compose smoke: C.4 runbook and ramp constants."""

from __future__ import annotations

from sate_live_l1.c4_runbook import C4_STEPS
from sate_live_l1.ramp import RAMP_FACTOR_L1_START, RAMP_MIN_DAYS


def main() -> None:
    if RAMP_FACTOR_L1_START != "0.25":
        raise SystemExit("L1 ramp must start at 0.25")
    if len(C4_STEPS) < 6:
        raise SystemExit("C.4 runbook incomplete")
    if RAMP_MIN_DAYS < 30:
        raise SystemExit("ramp minimum days too low")
    print("live-l1 ok")


if __name__ == "__main__":
    main()
