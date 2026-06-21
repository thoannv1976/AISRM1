"""Background worker entrypoint.

Run with: ``python -m app.worker``

- TASK_DRIVER=redis: consume tasks from the shared Redis list.
- otherwise: idle (the API processes tasks inline in local/dev).
"""
from __future__ import annotations

import json
import signal
import time

from app.core.config import settings
from app.services.task_handlers import handle
from app.services.tasks import QUEUE_KEY

_running = True


def _stop(*_):
    global _running
    _running = False


def run() -> None:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    if settings.task_driver.lower() != "redis":
        print("[worker] TASK_DRIVER is not 'redis'; API runs tasks inline. Worker idle.")
        while _running:
            time.sleep(2)
        return

    import redis

    r = redis.Redis.from_url(settings.redis_url)
    print(f"[worker] consuming from {QUEUE_KEY} on {settings.redis_url}")
    while _running:
        item = r.blpop(QUEUE_KEY, timeout=2)
        if not item:
            continue
        try:
            msg = json.loads(item[1])
            handle(msg["type"], msg.get("payload", {}))
        except Exception as exc:  # noqa: BLE001 - keep worker alive
            print(f"[worker] task failed: {exc}")


if __name__ == "__main__":
    run()
