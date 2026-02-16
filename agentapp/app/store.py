from __future__ import annotations

from threading import Lock
from uuid import UUID

from .models import ActionResult


class ActionStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._items: dict[UUID, ActionResult] = {}

    def upsert(self, result: ActionResult) -> None:
        with self._lock:
            self._items[result.request_id] = result

    def get(self, request_id: UUID) -> ActionResult | None:
        with self._lock:
            return self._items.get(request_id)
