from redis import Redis
from rq import Job, Queue

from app.core import settings

_redis: Redis | None = None
_queue: Queue | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def get_queue() -> Queue:
    global _queue
    if _queue is None:
        _queue = Queue("sangad-jobs", connection=get_redis())
    return _queue


def enqueue(func: str | callable, *args, **kwargs) -> Job:
    return get_queue().enqueue(func, *args, **kwargs)


def get_job(job_id: str) -> Job | None:
    try:
        return Job.fetch(job_id, connection=get_redis())
    except Exception:
        return None
