"""Issue halt commands and collect kernel acknowledgements."""

from __future__ import annotations

from sate_halt.drill import DrillLog
from sate_halt.protocol import HaltState, Protocol


class Coordinator:
    def __init__(self) -> None:
        self._commands: dict[str, Protocol] = {}
        self.drill = DrillLog()

    def issue(
        self,
        *,
        command_id: str,
        scope: str,
        kill_level: str,
        reason: str,
        channel: str,
        identity: str,
        b_reachable: bool = False,
    ) -> Protocol:
        if scope not in {"A", "B", "ALL"}:
            raise ValueError("explicit group scope required")
        if kill_level not in {"K1", "K2", "K3"}:
            raise ValueError("kill level must be K1, K2, or K3")
        command = Protocol(
            command_id=command_id,
            scope=scope,
            kill_level=kill_level,
            reason=reason,
            channel=channel,
            identity=identity,
            b_reachable=b_reachable,
        )
        self._commands[command_id] = command
        return command

    def ack_a(self, command_id: str) -> HaltState:
        command = self._require(command_id)
        command.confirmed_a = True
        return command.status()

    def ack_b(self, command_id: str) -> HaltState:
        command = self._require(command_id)
        if not command.b_reachable:
            raise ValueError("kernel B is unreachable")
        command.confirmed_b = True
        return command.status()

    def mark_b_unreachable(self, command_id: str) -> HaltState:
        command = self._require(command_id)
        command.b_reachable = False
        command.confirmed_b = False
        return command.status()

    def _require(self, command_id: str) -> Protocol:
        try:
            return self._commands[command_id]
        except KeyError as exc:
            raise ValueError("unknown halt command") from exc
