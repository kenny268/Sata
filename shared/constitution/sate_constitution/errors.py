"""Constitution load and activation failures."""


class ConstitutionError(ValueError):
    """The signature, the time-lock, or the version check refused the artifact."""

    def __init__(self, message: str, *, code: str = "rejected") -> None:
        super().__init__(message)
        self.code = code
