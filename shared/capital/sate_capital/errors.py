"""Capital ledger failures. Invalid input does not change the projection."""


class CapitalError(ValueError):
    """The event cannot be applied to this group's ledger."""
