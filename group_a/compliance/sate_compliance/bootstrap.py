"""Compose smoke: strict gate blocks incomplete verification."""

from __future__ import annotations

from sate_compliance.staging import complete_gate, incomplete_gate


def main() -> None:
    if not incomplete_gate().block_reasons():
        raise SystemExit("incomplete gate must block LIVE arm")
    if complete_gate().block_reasons():
        raise SystemExit("complete gate should allow LIVE arm")
    print("compliance ok")


if __name__ == "__main__":
    main()
