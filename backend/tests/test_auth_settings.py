"""The auth policy must be configurable, not baked into the code (R-17).

Every value the operator can tune has to come from the environment and
have to change the behaviour when it changes. These tests pin that link
in both directions: the setting is read from the environment, and the
runtime behaviour follows the setting.
"""
import re
from datetime import timedelta
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.kernel import models
from app.kernel.auth import lock_ttl_seconds
from tests.factories import make_user

PASSWORD = "correct-horse-1"

# Values injected through the environment in the first test.
ENV_FAILURE_LIMIT = 2
ENV_LOCKOUT_MINUTES = 7
ENV_OTP_EXPIRY_MINUTES = 9
ENV_OTP_MAX_ATTEMPTS = 3
ENV_SESSION_IDLE_MINUTES = 11
ENV_SESSION_ABSOLUTE_HOURS = 13

# Tolerances and window sizes used by the assertions.
TOLERANCE_SECONDS = 60
EARLY_FAILURE_LIMIT = 2
DEFAULT_FAILURE_LIMIT = 5
LOCKOUT_WINDOW_MINUTES = 3
LOCKOUT_WINDOW_SECONDS = LOCKOUT_WINDOW_MINUTES * 60
SMALL_OTP_ATTEMPTS = 2
LONG_OTP_EXPIRY_MINUTES = 30
SHORT_ABSOLUTE_HOURS = 4
IDLE_WINDOW_MINUTES = 45
IDLE_ELAPSED_MINUTES = IDLE_WINDOW_MINUTES + 1


def _otp_from_messages(messages: list[str]) -> str:
    codes: list[str] = re.findall(r"code is: (\d{6})", "\n".join(messages))
    assert codes, "email adapter should deliver the test OTP"
    return codes[-1]


def _login(api_client: TestClient, email_outbox: list[str]) -> str:
    response = api_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": PASSWORD},
    )
    assert response.status_code == HTTPStatus.OK
    return _otp_from_messages(email_outbox)


def test_settings_read_the_tunables_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """A value in the environment must reach the Settings object."""
    monkeypatch.setenv("LOGIN_FAILURE_LIMIT", str(ENV_FAILURE_LIMIT))
    monkeypatch.setenv("LOGIN_LOCKOUT_MINUTES", str(ENV_LOCKOUT_MINUTES))
    monkeypatch.setenv("OTP_EXPIRY_MINUTES", str(ENV_OTP_EXPIRY_MINUTES))
    monkeypatch.setenv("OTP_MAX_ATTEMPTS", str(ENV_OTP_MAX_ATTEMPTS))
    monkeypatch.setenv("SESSION_IDLE_MINUTES", str(ENV_SESSION_IDLE_MINUTES))
    monkeypatch.setenv("SESSION_ABSOLUTE_HOURS", str(ENV_SESSION_ABSOLUTE_HOURS))

    configured = Settings(
        database_url="postgresql+psycopg2://u:p@localhost/db",
        secret_key="test-secret",
    )

    assert configured.login_failure_limit == ENV_FAILURE_LIMIT
    assert configured.login_lockout_minutes == ENV_LOCKOUT_MINUTES
    assert configured.otp_expiry_minutes == ENV_OTP_EXPIRY_MINUTES
    assert configured.otp_max_attempts == ENV_OTP_MAX_ATTEMPTS
    assert configured.session_idle_minutes == ENV_SESSION_IDLE_MINUTES
    assert configured.session_absolute_hours == ENV_SESSION_ABSOLUTE_HOURS


def test_login_lockout_threshold_follows_the_setting(
    api_client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The number of failures before the lock follows LOGIN_FAILURE_LIMIT."""
    make_user(db, username="lock-early")
    make_user(db, username="lock-late")

    # Threshold 2: the second failure locks the account.
    monkeypatch.setattr(settings, "login_failure_limit", EARLY_FAILURE_LIMIT)
    early = [
        api_client.post(
            "/api/v1/auth/login",
            json={"username": "lock-early", "password": "wrong-password"},
        ).status_code
        for _ in range(EARLY_FAILURE_LIMIT)
    ]
    assert early == [HTTPStatus.UNAUTHORIZED, HTTPStatus.LOCKED]

    # Threshold 5: the same two failures do not lock, and only the fifth does.
    monkeypatch.setattr(settings, "login_failure_limit", DEFAULT_FAILURE_LIMIT)
    late = [
        api_client.post(
            "/api/v1/auth/login",
            json={"username": "lock-late", "password": "wrong-password"},
        ).status_code
        for _ in range(DEFAULT_FAILURE_LIMIT)
    ]
    assert late == [HTTPStatus.UNAUTHORIZED] * 4 + [HTTPStatus.LOCKED]


def test_login_lockout_window_follows_the_setting(
    api_client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The lock must expire after LOGIN_LOCKOUT_MINUTES, not a fixed 15."""
    make_user(db)
    monkeypatch.setattr(settings, "login_failure_limit", 1)
    monkeypatch.setattr(settings, "login_lockout_minutes", LOCKOUT_WINDOW_MINUTES)

    first = api_client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "wrong-password"}
    )
    assert first.status_code == HTTPStatus.LOCKED

    ttl = lock_ttl_seconds("admin")
    assert 0 < ttl <= LOCKOUT_WINDOW_SECONDS, (
        f"lock ttl {ttl}s does not follow the configured window"
    )


def test_otp_attempt_limit_follows_the_setting(
    api_client: TestClient,
    db: Session,
    email_outbox: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lowering OTP_MAX_ATTEMPTS must reject the code sooner."""
    make_user(db)
    monkeypatch.setattr(settings, "otp_max_attempts", SMALL_OTP_ATTEMPTS)

    code = _login(api_client, email_outbox)
    wrong = "000000" if code != "000000" else "000001"

    # With otp_max_attempts=2 the first two wrong codes are plain failures
    # and the third one is refused because the challenge is locked.
    for _ in range(SMALL_OTP_ATTEMPTS):
        attempt = api_client.post(
            "/api/v1/auth/verify-otp", json={"username": "admin", "otp": wrong}
        )
        assert attempt.status_code == HTTPStatus.UNAUTHORIZED
        assert attempt.json()["code"] == "invalid_otp"

    locked = api_client.post("/api/v1/auth/verify-otp", json={"username": "admin", "otp": wrong})
    assert locked.status_code == HTTPStatus.UNAUTHORIZED
    assert locked.json()["code"] == "otp_locked"


def test_otp_expiry_follows_the_setting(
    api_client: TestClient,
    db: Session,
    email_outbox: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The challenge must expire after the configured number of minutes."""
    make_user(db)
    monkeypatch.setattr(settings, "otp_expiry_minutes", LONG_OTP_EXPIRY_MINUTES)

    _login(api_client, email_outbox)

    challenge = (
        db.query(models.OtpChallenge)
        .filter(models.OtpChallenge.consumed_at.is_(None))
        .order_by(models.OtpChallenge.created_at.desc())
        .first()
    )
    assert challenge is not None
    created_at = challenge.created_at
    expires_at = challenge.expires_at
    assert created_at is not None
    assert expires_at is not None

    expected = created_at + timedelta(minutes=LONG_OTP_EXPIRY_MINUTES)
    assert abs((expires_at - expected).total_seconds()) < TOLERANCE_SECONDS


def test_session_absolute_lifetime_follows_the_setting(
    api_client: TestClient,
    db: Session,
    email_outbox: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The stored session must expire after the configured number of hours."""
    make_user(db)
    monkeypatch.setattr(settings, "session_absolute_hours", SHORT_ABSOLUTE_HOURS)

    code = _login(api_client, email_outbox)
    api_client.post("/api/v1/auth/verify-otp", json={"username": "admin", "otp": code})

    session = db.query(models.Session).order_by(models.Session.created_at.desc()).first()
    assert session is not None
    created_at = session.created_at
    expires_at = session.expires_at
    assert created_at is not None
    assert expires_at is not None

    expected = created_at + timedelta(hours=SHORT_ABSOLUTE_HOURS)
    assert abs((expires_at - expected).total_seconds()) < TOLERANCE_SECONDS


def test_session_idle_timeout_follows_the_setting(
    api_client: TestClient,
    db: Session,
    email_outbox: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A session idle for longer than the configured window is rejected."""
    make_user(db)
    monkeypatch.setattr(settings, "session_idle_minutes", IDLE_WINDOW_MINUTES)

    code = _login(api_client, email_outbox)
    api_client.post("/api/v1/auth/verify-otp", json={"username": "admin", "otp": code})
    assert api_client.get("/api/v1/auth/me").status_code == HTTPStatus.OK

    session = db.query(models.Session).order_by(models.Session.created_at.desc()).first()
    assert session is not None
    last_activity = session.last_activity
    assert last_activity is not None
    session.last_activity = last_activity - timedelta(minutes=IDLE_ELAPSED_MINUTES)
    db.commit()

    stale = api_client.get("/api/v1/auth/me")
    assert stale.status_code == HTTPStatus.UNAUTHORIZED
    assert stale.json()["code"] == "session_expired"
