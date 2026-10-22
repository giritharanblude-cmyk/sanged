"""The compose files must follow the deployment rules (R-22, R-26, R-17).

R-22 pins third-party runtimes to an explicit tag and forbids `:latest`.
The production compose must not open the SMTP sink to unauthenticated
clients, and every setting the operator can tune has to reach the API
service through the environment.

These checks read the compose files, which are not part of the image, so
the dev stack mounts them and points SANGAD_REPO_ROOT at the mount.
"""
import os
from pathlib import Path
from typing import Any

import pytest
import yaml

PRODUCTION_COMPOSE = "infra/coolify/docker-compose.yml"
DEV_COMPOSE = "docker-compose.dev.yml"


def _repo_root() -> Path:
    configured = os.environ.get("SANGAD_REPO_ROOT")
    if configured:
        return Path(configured)
    for candidate in Path(__file__).resolve().parents:
        if (candidate / PRODUCTION_COMPOSE).is_file():
            return candidate
    raise RuntimeError(
        "Cannot locate the repository root. Set SANGAD_REPO_ROOT to the directory "
        "holding the compose files."
    )


REPO_ROOT = _repo_root()


def _compose(name: str) -> dict[str, Any]:
    text = (REPO_ROOT / name).read_text(encoding="utf-8")
    parsed: dict[str, Any] = yaml.safe_load(text)
    return parsed


@pytest.mark.parametrize("compose_file", [PRODUCTION_COMPOSE, DEV_COMPOSE])
def test_every_image_is_pinned_to_an_explicit_tag(compose_file: str) -> None:
    """R-22: never :latest, always an explicit tag or digest."""
    services = _compose(compose_file).get("services") or {}
    unpinned: list[str] = []
    for service_name, config in services.items():
        image = config.get("image")
        if not image:
            continue
        tag = image.rsplit("/", 1)[-1]
        if ":" not in tag:
            unpinned.append(f"{service_name}: {image}")
    assert not unpinned, f"{compose_file} uses unpinned images: {unpinned}"


@pytest.mark.parametrize("compose_file", [PRODUCTION_COMPOSE, DEV_COMPOSE])
def test_no_image_uses_the_latest_tag(compose_file: str) -> None:
    services = _compose(compose_file).get("services") or {}
    latest = [
        f"{name}: {config['image']}"
        for name, config in services.items()
        if config.get("image") and str(config["image"]).endswith(":latest")
    ]
    assert not latest, f"{compose_file} uses :latest: {latest}"


def test_the_production_smtp_sink_is_not_open_to_any_client() -> None:
    """The mailpit service must not accept unauthenticated SMTP clients."""
    services = _compose(PRODUCTION_COMPOSE).get("services") or {}
    mailpit = services.get("mailpit") or {}
    env = mailpit.get("environment") or {}
    if isinstance(env, list):
        names = {entry.split("=", 1)[0] for entry in env if "=" in entry}
    else:
        names = set(env)
    forbidden = {"MP_SMTP_AUTH_ACCEPT_ANY", "MP_SMTP_AUTH_ALLOW_INSECURE"}
    assert not (names & forbidden), f"the SMTP sink still opens auth: {sorted(names & forbidden)}"


def test_the_production_api_service_receives_the_auth_policy_settings() -> None:
    """R-17: a setting an operator can tune has to reach the service."""
    services = _compose(PRODUCTION_COMPOSE).get("services") or {}
    api = services.get("api") or {}
    env = api.get("environment") or []
    if isinstance(env, dict):
        names = set(env)
    else:
        names = {entry.split("=", 1)[0] for entry in env if "=" in entry}
    for name in (
        "OTP_EXPIRY_MINUTES",
        "OTP_MAX_ATTEMPTS",
        "SESSION_IDLE_MINUTES",
        "SESSION_ABSOLUTE_HOURS",
        "LOGIN_FAILURE_LIMIT",
        "LOGIN_LOCKOUT_MINUTES",
    ):
        assert name in names, f"{name} does not reach the production api service"


def test_the_production_services_bind_to_loopback_only() -> None:
    """R-26: a published port must not be reachable from the network."""
    services = _compose(PRODUCTION_COMPOSE).get("services") or {}
    for service_name, config in services.items():
        for port in config.get("ports") or []:
            host = str(port).split(":")[0]
            assert host in {"127.0.0.1", "localhost"}, (
                f"{service_name} publishes {port} on a non-loopback address"
            )
