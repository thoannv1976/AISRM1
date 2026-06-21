"""Async task-queue abstraction: local (inline) / redis / Cloud Tasks.

The API enqueues jobs; in local/dev the LocalTaskQueue runs them inline so no
broker is required. With TASK_DRIVER=redis a separate worker consumes them.
"""

from __future__ import annotations

import json
from typing import Any

from app.core.config import settings

QUEUE_KEY = "aisrm1:tasks"


class TaskQueue:
    def enqueue(self, task_type: str, payload: dict[str, Any]) -> None:
        raise NotImplementedError


class LocalTaskQueue(TaskQueue):
    """Runs the handler inline (used by API in dev when no broker is present)."""

    def enqueue(self, task_type: str, payload: dict[str, Any]) -> None:
        from app.services.task_handlers import handle

        handle(task_type, payload)


class RedisTaskQueue(TaskQueue):
    def __init__(self, url: str):
        import redis  # lazy import

        self._r = redis.Redis.from_url(url)

    def enqueue(self, task_type: str, payload: dict[str, Any]) -> None:
        self._r.rpush(QUEUE_KEY, json.dumps({"type": task_type, "payload": payload}))


_instance: TaskQueue | None = None


def get_queue() -> TaskQueue:
    global _instance
    if _instance is None:
        if settings.task_driver.lower() == "redis":
            try:
                _instance = RedisTaskQueue(settings.redis_url)
            except Exception:  # noqa: BLE001 - fall back to inline
                _instance = LocalTaskQueue()
        else:
            _instance = LocalTaskQueue()
    return _instance
