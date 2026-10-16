"""Security middleware tests."""

from http import HTTPStatus

from fakeredis import FakeRedis
from fastapi import FastAPI
from fastapi.testclient import TestClient
from redis import Redis

from app.core.middleware import CsrfMiddleware, RateLimitMiddleware
from app.kernel.jobs import get_redis


def test_rate_limit_uses_redis_and_counts_auth_routes(fake_redis: FakeRedis) -> None:
    app = FastAPI()

    @app.post("/api/v1/auth/login")
    def login() -> dict[str, str]:
        return {"status": "ok"}

    client_app = RateLimitMiddleware(app, max_requests=1, window_seconds=60)
    with TestClient(client_app) as client:
        assert client.post("/api/v1/auth/login").status_code == HTTPStatus.OK
        assert (
            client.post("/api/v1/auth/login").status_code
            == HTTPStatus.TOO_MANY_REQUESTS
        )

    assert list(fake_redis.scan_iter(match="sangad:ratelimit:*"))


def test_rate_limit_uses_live_redis(live_test_redis: Redis) -> None:
    assert get_redis().ping()
    app = FastAPI()

    @app.post("/api/v1/auth/login")
    def login() -> dict[str, str]:
        return {"status": "ok"}

    with TestClient(RateLimitMiddleware(app, max_requests=1, window_seconds=60)) as client:
        assert client.post("/api/v1/auth/login").status_code == HTTPStatus.OK
        limited = client.post("/api/v1/auth/login")

    assert limited.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert list(live_test_redis.scan_iter(match="sangad:ratelimit:*"))


def test_csrf_blocks_unsafe_requests_without_double_submit_token() -> None:
    app = FastAPI()

    @app.post("/api/v1/auth/login")
    def login() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/payslip/payslips")
    def create_payslip() -> dict[str, str]:
        return {"status": "created"}

    with TestClient(CsrfMiddleware(app)) as client:
        assert client.post("/api/v1/auth/login").status_code == HTTPStatus.OK
        assert (
            client.post("/api/v1/payslip/payslips").status_code
            == HTTPStatus.FORBIDDEN
        )
        client.cookies.set("csrf_token", "token-value")
        response = client.post(
            "/api/v1/payslip/payslips",
            headers={"x-csrf-token": "token-value"},
        )
        assert response.status_code == HTTPStatus.OK
