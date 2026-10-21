"""Append-only fact log."""

from sate_factlog.errors import FactLogWriteError, Unauthorized
from sate_factlog.log import EVENT_TYPES, FactLog, open_log

__all__ = ["EVENT_TYPES", "FactLog", "FactLogWriteError", "Unauthorized", "open_log"]
