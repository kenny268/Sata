"""Fact-log boundary for a KERNEL-A verdict. The broker mock cannot run ahead of the log."""

from sate_runtime.journal import GateError, persist_verdict, submit_persisted

__all__ = [
    "GateError",
    "persist_verdict",
    "submit_persisted",
]
