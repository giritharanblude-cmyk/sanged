"""Redis connection facade + RQ queue access (kernel T-005).

One creation point for the Redis client so config, decode policy and the
sync-command typing quirks of redis-py are handled in a single module.

redis-py 5.x types every command's return as ``Union[Awaitable[Any], Any]``
(redis/typing.py ResponseT) because the same method table serves the asyncio
client. We only ever use the sync client, so the values are narrowed to the
documented sync types below rather than sprinkling casts across the codebase.
"""
from collections.abc import Callable
from typing import Any, cast

from redis import Redis
from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq.queue import Queue

from app.core.config import settings

_redis: Redis | None = None
_queue: Queue | None = None

# The lazily-created process-wide singletons are intentional: FastAPI imports
# this module before .env values settle in test harnesses that patch settings.
# Pylint-style global-discouragement does not apply to this caching idiom.
def get_redis() -> Redis:
    """The process-wide sync Redis client (decode_responses for str values)."""
    global _redis  # noqa: PLW0603 - deliberate lazy singleton (see comment above)
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def redis_int(value: Any) -> int:
    """Narrow a sync Redis reply to int (INCR/EXISTS/TTL return integral types)."""
    return int(cast(int, value))


def redis_str(value: Any) -> str:
    """Narrow a sync Redis reply to str (decode_responses=True)."""
    return str(cast(str, value))


def redis_delete(*keys: str) -> int:
    return redis_int(get_redis().delete(*keys))


def redis_setex(key: str, seconds: int, value: str) -> None:
    get_redis().set(key, value, ex=seconds)


def redis_exists(key: str) -> bool:
    return redis_int(get_redis().exists(key)) > 0


def redis_incr(key: str) -> int:
    return redis_int(get_redis().incr(key))


def redis_ttl(key: str) -> int:
    return redis_int(get_redis().ttl(key))


def get_queue() -> Queue:
    """The sangad-jobs queue; same queue name the worker boots with."""
    global _queue  # noqa: PLW0603 - deliberate lazy singleton (see comment above)
    if _queue is None:
        queue_connection = Redis.from_url(settings.redis_url)
        _queue = Queue("sangad-jobs", connection=queue_connection)
    return _queue


def enqueue_by_name(func_name: str, *args: Any, **kwargs: Any) -> Job:
    """Enqueue a worker-module function by its dotted path."""
    return get_queue().enqueue(func_name, *args, **kwargs)


def enqueue(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Job:
    """Enqueue a callable directly (typed path)."""
    return get_queue().enqueue(func, *args, **kwargs)


def get_job(job_id: str) -> Job | None:
    try:
        return Job.fetch(job_id, connection=get_queue().connection)
    except NoSuchJobError:
        return None
