"""Group A account registry. Default scope is A. Other groups are rejected."""

from sate_identity.registry import IdentityRegistry, open_registry
from sate_identity.errors import IsolationError

__all__ = ["IdentityRegistry", "IsolationError", "open_registry"]
