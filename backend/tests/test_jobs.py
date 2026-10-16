"""Redis-backed queue tests for the RQ job runner."""

from uuid import uuid4

import pytest
from redis import Redis
from rq import Queue, SimpleWorker

from app.core.config import settings
from app.kernel import jobs

EXPECTED_SUM = 42


def add_values(left: int, right: int) -> int:
    return left + right


def test_enqueued_job_runs_and_is_retrievable(
    live_test_redis: Redis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del live_test_redis
    queue_connection = Redis.from_url(settings.redis_url)
    monkeypatch.setattr(jobs, "_queue", Queue("sangad-jobs", connection=queue_connection))
    try:
        enqueued = jobs.enqueue(add_values, 20, 22)
        worker = SimpleWorker([jobs.get_queue()], connection=queue_connection)
        worker.work(burst=True, with_scheduler=False)

        completed = jobs.get_job(enqueued.id)
        assert completed is not None
        assert completed.is_finished
        assert completed.return_value() == EXPECTED_SUM
        assert jobs.get_job(str(uuid4())) is None
    finally:
        queue_connection.close()
