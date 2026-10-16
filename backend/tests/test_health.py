"""Health/readiness endpoints."""
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.core.config import settings
from app.main import app


def test_healthz_ok(api_client: TestClient) -> None:
    res = api_client.get("/healthz")
    assert res.status_code == HTTPStatus.OK
    assert res.json() == {"status": "ok"}


def test_readyz_probes_db_redis_and_storage(api_client: TestClient) -> None:
    """V-PLAT-02: readiness verifies all configured critical dependencies."""
    res = api_client.get("/readyz")
    assert res.status_code == HTTPStatus.OK
    body = res.json()
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["redis"] == "ok"
    assert body["checks"]["storage"] == "ok"
    assert body["status"] == "ok"


def test_readyz_fails_when_redis_down(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken_redis() -> None:
        raise ConnectionError("redis is down")

    monkeypatch.setattr(main_module, "get_redis", broken_redis)
    res = api_client.get("/readyz")
    assert res.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert res.json()["checks"]["redis"].startswith("error:")


def test_readyz_fails_when_storage_down(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken_storage() -> None:
        raise OSError("storage is down")

    monkeypatch.setattr(main_module, "probe_storage", broken_storage)
    res = api_client.get("/readyz")
    assert res.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert res.json()["checks"]["storage"].startswith("error:")


def test_readyz_fails_when_s3_storage_is_unreachable(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "storage_backend", "s3")
    monkeypatch.setattr(settings, "s3_endpoint_url", "")

    res = api_client.get("/readyz")

    assert res.status_code == HTTPStatus.SERVICE_UNAVAILABLE
    assert res.json()["checks"]["storage"] == "error: ValueError"


def test_version_endpoint_requires_auth(
    api_client: TestClient, authenticated_client: TestClient
) -> None:
    del authenticated_client
    with TestClient(app) as anonymous_client:
        denied = anonymous_client.get("/api/v1/version")
    assert denied.status_code == HTTPStatus.UNAUTHORIZED
    res = api_client.get("/api/v1/version")
    assert res.status_code == HTTPStatus.OK
    assert res.json()["version"]
