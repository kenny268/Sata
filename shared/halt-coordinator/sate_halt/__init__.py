"""Halt coordinator. Group B unreachable must not become HALT_CONFIRMED_ALL."""

from sate_halt.protocol import HaltState, Protocol
from sate_halt.service import Coordinator

__all__ = ["Coordinator", "HaltState", "Protocol"]
