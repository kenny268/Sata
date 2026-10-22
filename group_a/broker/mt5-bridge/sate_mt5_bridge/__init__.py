"""The bridge normalises the terminal. It does not hold trade credentials."""

from sate_mt5_bridge.bridge import DEMO_SESSIONS, Bridge
from sate_mt5_bridge.errors import AdapterError
from sate_mt5_bridge.frames import decode_frame, encode_frame, refuse_dealer
from sate_mt5_bridge.terminal import MockTerminal

__all__ = [
    "DEMO_SESSIONS",
    "AdapterError",
    "Bridge",
    "MockTerminal",
    "decode_frame",
    "encode_frame",
    "refuse_dealer",
]
