"""Shared fixtures backed by a disposable PostgreSQL database and fakeredis."""

import os
import re
from collections.abc import Generator, Iterator
from http import HTTPStatus
from pathlib import Path
from urllib.parse import urlparse

import pytest
from fakeredis import FakeRedis
from fastapi.testclient import TestClient
from redis import Redis
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

import app.main as main_module
from app.core.config import settings
from app.core.db import SessionLocal, engine, get_db
from app.kernel.models import Base
from tests.factories import make_user


@pytest.fixture(scope="session")
def db_engine() -> Iterator[Engine]:
    """Create schema only in a database explicitly named for testing."""
    database_name = Path(urlparse(settings.database_url).path).name
    if not database_name.endswith("_test"):
        raise RuntimeError("Tests require a dedicated DATABASE_URL ending in _test")
    Base.metadata.create_all(bind=engine)
    app_role = os.environ.get("APP_DB_USER")
    if not app_role:
        raise RuntimeError("APP_DB_USER is required to validate audit-log privileges")
    quoted_app_role = engine.dialect.identifier_preparer.quote(app_role)
    with engine.begin() as connection:
        connection.execute(
            text(
                "GRANT SELECT, INSERT, UPDATE, DELETE "
                f"ON ALL TABLES IN SCHEMA public TO {quoted_app_role}"
            )
        )
        connection.execute(
            text(f"REVOKE UPDATE, DELETE ON TABLE public.audit_log FROM {quoted_app_role}")
        )
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def app_role_engine(db_engine: Engine) -> Iterator[Engine]:
    del db_engine
    app_database_url = os.environ.get("APP_TEST_DATABASE_URL")
    if not app_database_url:
        raise RuntimeError("APP_TEST_DATABASE_URL is required for role tests")
    app_engine = create_engine(app_database_url, pool_pre_ping=True)
    try:
        yield app_engine
    finally:
        app_engine.dispose()


@pytest.fixture()
def db(db_engine: Engine) -> Generator[Session, None, None]:
    """Wrap each test in a transaction that is rolled back after the test."""
    if db_engine is not engine:
        raise RuntimeError("Test fixtures must use the configured test engine")
    connection = db_engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> Generator[FakeRedis, None, None]:
    """Isolate unit tests that specifically exercise Redis middleware."""
    server = FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.kernel.jobs._redis", server, raising=True)
    monkeypatch.setattr("app.kernel.jobs.get_redis", lambda: server, raising=True)
    try:
        yield server
    finally:
        server.flushall()


@pytest.fixture()
def live_test_redis() -> Iterator[Redis]:
    """Use only the dedicated Redis database reserved for integration tests."""
    if urlparse(settings.redis_url).path != "/1":
        raise RuntimeError("Integration tests require REDIS_URL to use Redis database 1")
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    client.flushdb()
    try:
        yield client
    finally:
        client.flushdb()
        client.close()


@pytest.fixture(autouse=True)
def email_outbox(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Capture delivered test email bodies without writing OTPs to logs."""
    messages: list[str] = []

    def capture_email(to: str, subject: str, body: str) -> bool:
        del to, subject
        messages.append(body)
        return True

    monkeypatch.setattr("app.kernel.auth.send_email", capture_email)
    return messages


@pytest.fixture()
def api_client(
    db: Session,
    live_test_redis: Redis,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Iterator[TestClient]:
    """Exercise the real FastAPI application with test-only service adapters."""
    del live_test_redis

    def override_db() -> Iterator[Session]:
        yield db

    monkeypatch.setattr(settings, "cookie_secure", False)
    monkeypatch.setattr(settings, "storage_backend", "filesystem")
    monkeypatch.setattr(settings, "storage_path", str(tmp_path))
    main_module.app.dependency_overrides[get_db] = override_db
    settings.allowed_hosts.append("testserver")
    client = TestClient(main_module.app)
    try:
        yield client
    finally:
        client.close()
        main_module.app.dependency_overrides.clear()
        settings.allowed_hosts.remove("testserver")


@pytest.fixture()
def authenticated_client(
    api_client: TestClient,
    db: Session,
    email_outbox: list[str],
) -> TestClient:
    """Create a session by completing the real password + OTP API flow."""
    make_user(db)
    login = api_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "correct-horse-1"},
    )
    if login.status_code != HTTPStatus.OK:
        raise AssertionError("Test admin login did not issue an OTP")
    codes = re.findall(r"code is: (\d{6})", "\n".join(email_outbox))
    if not codes:
        raise AssertionError("Test email adapter did not capture the login OTP")
    verified = api_client.post(
        "/api/v1/auth/verify-otp",
        json={"username": "admin", "otp": codes[-1]},
    )
    if verified.status_code != HTTPStatus.OK:
        raise AssertionError("Test admin OTP verification did not create a session")
    return api_client
