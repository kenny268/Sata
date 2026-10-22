"""RCB service failures. Nothing is ratified when one is raised."""


class RcbError(ValueError):
    """The cool-off, the passkey, or the scope check refused the change."""

    def __init__(self, message: str, *, code: str = "rejected") -> None:
        super().__init__(message)
        self.code = code
