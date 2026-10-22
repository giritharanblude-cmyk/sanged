"""The security behaviours that the rest of the suite does not cover.

Each test here pins one rule that the build plan and the architecture
require, and that had no test before:

  * an OTP issued for one purpose cannot be used for another
  * a session dies when its user is deactivated
  * the Bearer header is only honoured in a local environment
  * a request with an unknown Host header is refused
  * every response carries the hardening headers
  * the rate limiter does not throttle the health endpoints
  * readiness fails when the database is unreachable
"""
import re
from http import HTTPStatus

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from redis import Redis
from sqlalchemy.orm import Session

import app.main as main_module
from app.core.config import settings
from app.core.middleware import RateLimitMiddleware
from app.kernel import models
from app.kernel.auth import issue_otp
from app.kernel.jobs import get_redis

PASSWORD = "correct-horse-1"


def _otp_from_messages(messages: list[str]) -> str:
    codes: list[str] = re.findall(r"code is: (\d{6})", "\n".join(messages))
    assert codes, "email adapter should deliver the test OTP"
    return codes[-1]


def _csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get("csrf_token")
    assert token
    return {"x-csrf-token": token}


def _clear_otp_cooldowns() -> None:
    """Let a test request an extra challenge without waiting out the cooldown."""
    redis_client = get_redis()
    for key in redis_client.scan_iter(match="sangad:otpcooldown:*"):
        redis_client.delete(key)


def test_a_login_otp_cannot_be_used_to_change_the_password(
    authenticated_client: TestClient, db: Session, email_outbox: list[str]
) -> None:
    """An OTP is bound to its purpose; a login code is not a password-change code."""
    headers = _csrf_headers(authenticated_client)

    # Issue a fresh login-purpose challenge. It is issued through the kernel
    # so the resend cooldown does not get in the way of the test.
    user = db.query(models.User).filter(models.User.username == "admin").one()
    _clear_otp_cooldowns()
    issue_otp(db, user, "login")
    login_code = _otp_from_messages(email_outbox)

    # No password-change challenge exists, so the only open challenge is the
    # login one and it must not be accepted here.
    rejected = authenticated_client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={
            "current_password": PASSWORD,
            "new_password": "brand-new-pass-1",
            "otp": login_code,
        },
    )
    assert rejected.status_code == HTTPStatus.FORBIDDEN
    assert rejected.json()["code"] == "otp_required"

    # The password has not changed.
    _clear_otp_cooldowns()
    still_old = authenticated_client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": PASSWORD}
    )
    assert still_old.status_code == HTTPStatus.OK


def test_a_login_otp_is_rejected_when_a_password_change_is_pending(
    authenticated_client: TestClient, db: Session, email_outbox: list[str]
) -> None:
    """Even with a password-change challenge open, the login code is wrong."""
    headers = _csrf_headers(authenticated_client)

    user = db.query(models.User).filter(models.User.username == "admin").one()
    _clear_otp_cooldowns()
    issue_otp(db, user, "login")
    login_code = _otp_from_messages(email_outbox)

    authenticated_client.post("/api/v1/auth/change-password/init", headers=headers)
    change_code = _otp_from_messages(email_outbox)
    assert change_code != login_code

    rejected = authenticated_client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={
            "current_password": PASSWORD,
            "new_password": "brand-new-pass-1",
            "otp": login_code,
        },
    )
    assert rejected.status_code == HTTPStatus.UNAUTHORIZED
    assert rejected.json()["code"] == "invalid_otp"


def test_a_session_dies_when_the_user_is_deactivated(
    authenticated_client: TestClient, db: Session
) -> None:
    """Deactivating the user must invalidate the live session."""
    assert authenticated_client.get("/api/v1/auth/me").status_code == HTTPStatus.OK

    user = db.query(models.User).filter(models.User.username == "admin").one()
    user.is_active = False
    db.commit()

    rejected = authenticated_client.get("/api/v1/auth/me")
    assert rejected.status_code == HTTPStatus.UNAUTHORIZED
    assert rejected.json()["code"] == "user_inactive"


def test_the_bearer_header_is_accepted_in_a_local_environment(
    authenticated_client: TestClient,
) -> None:
    """The Bearer form exists for local tests and command line tooling."""
    token = authenticated_client.cookies.get("session")
    assert token

    # Drop the cookie so only the header can authenticate the request.
    authenticated_client.cookies.clear()
    assert settings.is_local, "the test environment must be local"
    allowed = authenticated_client.get(
        "/api/v1/auth/me", headers={"authorization": f"Bearer {token}"}
    )
    assert allowed.status_code == HTTPStatus.OK


def test_the_bearer_header_is_refused_outside_a_local_environment(
    authenticated_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Outside a local environment the session must come from the cookie."""
    token = authenticated_client.cookies.get("session")
    assert token

    authenticated_client.cookies.clear()
    monkeypatch.setattr(settings, "app_env", "production")
    refused = authenticated_client.get(
        "/api/v1/auth/me", headers={"authorization": f"Bearer {token}"}
    )
    assert refused.status_code == HTTPStatus.UNAUTHORIZED
    assert refused.json()["code"] == "unauthorized"


def test_an_unknown_host_header_is_refused(api_client: TestClient) -> None:
    """The TrustedHost allowlist must reject a request for another host."""
    response = api_client.get("/healthz", headers={"host": "evil.example.com"})
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_the_security_headers_are_present(api_client: TestClient) -> None:
    response = api_client.get("/healthz")
    assert response.status_code == HTTPStatus.OK
    headers = response.headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["X-XSS-Protection"] == "1; mode=block"
    assert headers["Content-Security-Policy"] == "default-src 'self'"
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert headers["Permissions-Policy"] == "camera=(), microphone=()"


def test_the_rate_limiter_does_not_throttle_the_health_endpoints(
    live_test_redis: Redis,
) -> None:
    """/healthz and /readyz must stay reachable when a client is throttled."""
    del live_test_redis
    app = FastAPI()

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/version")
    def version() -> dict[str, str]:
        return {"version": "0.1.0"}

    limited = RateLimitMiddleware(app, max_requests=1, window_seconds=60)
    with TestClient(limited) as client:
        for _ in range(5):
            assert client.get("/healthz").status_code == HTTPStatus.OK
            assert client.get("/readyz").status_code == HTTPStatus.OK
        assert client.get("/api/v1/version").status_code == HTTPStatus.OK
        assert (
            client.get("/api/v1/version").status_code == HTTPStatus.TOO_MANY_REQUESTS
        )


def test_readyz_fails_when_the_database_is_down(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A database that cannot answer must make the service unready."""

    def broken_database() -> None:
        raise RuntimeError("database is down")
    monkeypatch.setattr(main_module, "SessionLocal", broken_database)
    response = api_client.get("/readyz")
    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["database"].startswith("error:")
