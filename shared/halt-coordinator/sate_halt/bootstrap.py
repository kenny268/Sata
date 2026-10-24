"""Phase 15 bootstrap. No broker credentials."""

from __future__ import annotations

from sate_halt.service import Coordinator


def main() -> None:
    coordinator = Coordinator()
    command = coordinator.issue(
        command_id="bootstrap-1",
        scope="A",
        kill_level="K1",
        reason="bootstrap",
        channel="internal",
        identity="halt-coordinator",
    )
    print(coordinator.ack_a(command.command_id).value)


if __name__ == "__main__":
    main()
