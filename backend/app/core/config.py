import ipaddress
import json
import os
from typing import Annotated, Any, Literal

from dotenv import dotenv_values
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode


def _is_loopback_host(host: str) -> bool:
    normalized = host.strip().strip("[]").lower()
    if normalized == "localhost" or normalized.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


class Settings(BaseSettings):
    app_env: str = "local"
    debug: bool = False
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str
    # NoDecode: env vars arrive as raw strings. Without it pydantic-settings
    # JSON-decodes complex fields, so a plain ALLOWED_HOSTS=sangad.localhost
    # raises SettingsError instead of parsing.
    allowed_hosts: Annotated[list[str], NoDecode] = ["sangad.localhost"]
    cookie_secure: bool = True
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    # Local SMTP sinks (Mailpit) speak plain SMTP on 1025 with no auth, so
    # STARTTLS and LOGIN must be opt-in rather than unconditional.
    smtp_starttls: bool = True
    s3_endpoint_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket_files: str = "sangad-files"
    s3_bucket_backups: str = "sangad-backups"
    s3_force_path_style: bool = True
    storage_backend: Literal["s3", "filesystem"] = "s3"
    storage_path: str = "/var/lib/sangad/storage"
    encryption_key: str = ""
    openwa_api_url: str = ""
    openwa_api_key: str = ""
    openwa_webhook_secret: str = ""
    extraction_provider: str = "llm"
    llm_api_key: str = ""
    llm_api_url: str = ""
    # Auth policy (ported from the phase-3 branch).
    otp_expiry_minutes: int = 5
    otp_max_attempts: int = 5
    session_idle_minutes: int = 30
    session_absolute_hours: int = 12
    # Bootstrap admin, used only by `python -m app.seed`.
    admin_username: str = "admin"
    admin_email: str = "admin@sangad.localhost"
    admin_password: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def session_lifetime_seconds(self) -> int:
        """Absolute session cap in seconds (single source of truth for cookies)."""
        return self.session_absolute_hours * 3600

    @property
    def is_local(self) -> bool:
        return self.app_env == "local"

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def _parse_allowed_hosts(cls, value: Any) -> Any:
        """Accept a JSON list, a comma-separated list, or a single host."""
        if not isinstance(value, str):
            return value
        raw = value.strip()
        if not raw:
            return []
        if raw.startswith("["):
            return json.loads(raw)
        return [host.strip() for host in raw.split(",") if host.strip()]

    @model_validator(mode="after")
    def validate_transport_settings(self) -> "Settings":
        """Keep insecure cookies limited to a local-only host configuration."""
        if "cookie_secure" not in self.model_fields_set:
            self.cookie_secure = not self.is_local
        if self.cookie_secure:
            return self
        if not self.is_local:
            raise ValueError("COOKIE_SECURE=false is only permitted with APP_ENV=local")
        if any(not _is_loopback_host(host) for host in self.allowed_hosts):
            raise ValueError("COOKIE_SECURE=false requires loopback-only ALLOWED_HOSTS")
        return self


_dotenv_values = dotenv_values(".env")


def _required_setting(name: str) -> str:
    value = os.environ.get(name, _dotenv_values.get(name))
    if value is None or not value.strip():
        raise ValueError(f"{name} is required")
    return value


settings = Settings(
    database_url=_required_setting("DATABASE_URL"),
    secret_key=_required_setting("SECRET_KEY"),
)
