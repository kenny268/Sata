"""Fact-log failures. A failed write never returns a fabricated event."""


class Unauthorized(PermissionError):
    """The writer is not allowed to append."""


class FactLogWriteError(RuntimeError):
    def __init__(self, message: str, *, policy: str) -> None:
        super().__init__(message)
        self.policy = policy
