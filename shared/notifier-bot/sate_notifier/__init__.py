"""Reduce-only Telegram notifier (**Phase 18**)."""

from sate_notifier.alive import handle_alive
from sate_notifier.bot import NotifierBot

__all__ = ["NotifierBot", "handle_alive"]
