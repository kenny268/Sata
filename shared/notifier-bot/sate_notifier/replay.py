"""SEC-02 replay deduplication."""

from __future__ import annotations

from collections import deque


class ReplayGuard:
    def __init__(self, capacity: int = 256) -> None:
        self._capacity = capacity
        self._seen: deque[int] = deque()

    def accept(self, update_id: int) -> bool:
        if update_id in self._seen:
            return False
        self._seen.append(update_id)
        while len(self._seen) > self._capacity:
            self._seen.popleft()
        return True
