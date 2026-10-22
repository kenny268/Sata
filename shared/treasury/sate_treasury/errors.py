"""Treasury failures. A rejected transition does not complete a reimbursement."""


class TreasuryError(ValueError):
    """The treasury event cannot be applied."""
