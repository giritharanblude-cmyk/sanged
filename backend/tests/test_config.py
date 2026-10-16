"""Configuration validation tests for transport security."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_accept_shared_env_with_compose_only_values() -> None:
    configured = Settings.model_validate(
        {
            "database_url": "postgresql+psycopg2://localhost/sangad_test",
            "secret_key": "test-only-secret",
            "postgres_db": "sangad",
        }
    )

    assert configured.database_url == "postgresql+psycopg2://localhost/sangad_test"


def test_local_environment_defaults_to_loopback_insecure_cookies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    configured = Settings.model_validate(
        {
            "app_env": "local",
            "database_url": "postgresql+psycopg2://test:test@localhost/sangad_test",
            "secret_key": "test-only-secret",
            "allowed_hosts": ["127.0.0.1", "localhost"],
        }
    )
    assert configured.cookie_secure is False


def test_non_local_environment_defaults_to_secure_cookies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    configured = Settings.model_validate(
        {
            "app_env": "production",
            "database_url": "postgresql+psycopg2://test:test@localhost/sangad_test",
            "secret_key": "test-only-secret",
            "allowed_hosts": ["sangad.example"],
        }
    )
    assert configured.cookie_secure is True


@pytest.mark.parametrize(
    "app_env, allowed_hosts",
    [
        ("production", ["sangad.example"]),
        ("local", ["sangad.example"]),
    ],
)
def test_insecure_cookies_are_rejected_outside_loopback_local(
    app_env: str,
    allowed_hosts: list[str],
) -> None:
    with pytest.raises(ValidationError, match="COOKIE_SECURE=false"):
        Settings.model_validate(
            {
                "app_env": app_env,
                "database_url": "postgresql+psycopg2://test:test@localhost/sangad_test",
                "secret_key": "test-only-secret",
                "allowed_hosts": allowed_hosts,
                "cookie_secure": False,
            }
        )
