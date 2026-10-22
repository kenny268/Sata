"""Release failures. An unsigned or unverified kernel does not become active."""


class ReleaseError(ValueError):
    """The build signature, the deploy authorization, or the red-team gate refused."""

    def __init__(self, message: str, *, code: str = "rejected") -> None:
        super().__init__(message)
        self.code = code
