"""Small in-process registry for truthful, coarse validation stage updates."""

from __future__ import annotations

from threading import Lock
from time import monotonic
from uuid import UUID

_EXPIRY_SECONDS = 600
_lock = Lock()
_stages: dict[str, tuple[str, float]] = {}


def publish_stage(run_id: UUID, stage: str) -> None:
    now = monotonic()
    with _lock:
        expired = [key for key, (_, updated) in _stages.items() if now - updated > _EXPIRY_SECONDS]
        for key in expired:
            _stages.pop(key, None)
        _stages[str(run_id)] = (stage, now)


def read_stage(run_id: UUID) -> str | None:
    now = monotonic()
    key = str(run_id)
    with _lock:
        item = _stages.get(key)
        if item is None:
            return None
        stage, updated = item
        if now - updated > _EXPIRY_SECONDS:
            _stages.pop(key, None)
            return None
        return stage
