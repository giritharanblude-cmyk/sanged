import json

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode
from typing import Annotated, Any, List


class Settings(BaseSettings):
    app_env: str = "local"
    debug: bool = False
    database_url: str = "postgresql+psycopg2://sangad:sangad@localhost:5432/sangad"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me-in-production"
    # NoDecode: env vars arrive as raw strings. Without it pydantic-settings
    # JSON-decodes complex fields, so a plain ALLOWED_HOSTS=sangad.localhost
    # raises SettingsError instead of parsing.
    allowed_hosts: Annotated[List[str], NoDecode] = ["sangad.localhost"]
    cookie_secure: bool = False
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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

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


settings = Settings()