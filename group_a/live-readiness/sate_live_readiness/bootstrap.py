"""Compose smoke: strict LIVE preflight blocks until staging complete inputs."""

from __future__ import annotations

from sate_live_readiness.staging import complete_assessment, incomplete_assessment


def main() -> None:
    if not incomplete_assessment().block_reasons():
        raise SystemExit("incomplete LIVE preflight must block")
    if complete_assessment().block_reasons():
        raise SystemExit("staging complete LIVE preflight should pass")
    print("live-readiness ok")


if __name__ == "__main__":
    main()
