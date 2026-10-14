from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from typing import Any

from app.core.settings import get_settings

try:
    import redis.asyncio as redis
except ImportError:  # pragma: no cover - dependency is optional at runtime
    redis = None

_local_subscribers: dict[str, set[asyncio.Queue[str]]] = {}
_redis_client: Any | None = None
_redis_failed = False


async def _get_redis_client() -> Any | None:
    global _redis_client, _redis_failed
    if redis is None or _redis_failed:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        client = redis.from_url(
            get_settings().redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=0.25,
            socket_timeout=0.25,
        )
        await client.ping()
    except Exception:
        _redis_failed = True
        return None
    _redis_client = client
    return client


async def publish_station_event(station_id: str, event: dict[str, Any]) -> None:
    channel = _station_channel(station_id)
    payload = json.dumps(event, default=str)
    for queue in list(_local_subscribers.get(channel, set())):
        queue.put_nowait(payload)

    client = await _get_redis_client()
    if client is not None:
        with suppress(Exception):
            await client.publish(channel, payload)


@asynccontextmanager
async def station_subscription(station_id: str) -> AsyncGenerator[asyncio.Queue[str], None]:
    channel = _station_channel(station_id)
    queue: asyncio.Queue[str] = asyncio.Queue()
    _local_subscribers.setdefault(channel, set()).add(queue)

    client = await _get_redis_client()
    pubsub = None
    task: asyncio.Task[None] | None = None
    if client is not None:
        pubsub = client.pubsub()
        await pubsub.subscribe(channel)
        task = asyncio.create_task(_forward_redis_messages(pubsub, queue))

    try:
        yield queue
    finally:
        _local_subscribers.get(channel, set()).discard(queue)
        if task is not None:
            task.cancel()
        if pubsub is not None:
            await pubsub.aclose()


async def _forward_redis_messages(pubsub: Any, queue: asyncio.Queue[str]) -> None:
    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
        if message is None:
            continue
        data = message.get("data")
        if isinstance(data, str):
            queue.put_nowait(data)


def _station_channel(station_id: str) -> str:
    return f"station:{station_id}"
