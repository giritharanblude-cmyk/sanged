from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    debug: bool = False
    secret: str = "insecure-change-me"
    database_url: str = "postgresql://sangad:sangad@localhost:5432/sangad"
    redis_url: str = "redis://localhost:6379/0"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "SANGAD <noreply@sangad.local>"
    field_encryption_key: str = "00000000000000000000000000000000"
    app_env: str = "local"
    allowed_hosts: list[str] = ["sangad.localhost", "localhost", "127.0.0.1"]
    cookie_secure: bool = False
    s3_endpoint_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket_files: str = "sangad-files"
    s3_bucket_backups: str = "sangad-backups"
    s3_force_path_style: bool = True
    openwa_base_url: str = "http://openwa:3000"
    openwa_api_key: str = ""
    openwa_webhook_secret: str = ""
    otp_expiry_minutes: int = 5
    otp_max_attempts: int = 5
    session_idle_minutes: int = 30
    session_absolute_hours: int = 12

    model_config = {"env_prefix": "sangad_", "env_file": ".env", "extra": "ignore"}

    @property
    def is_local(self) -> bool:
        return self.app_env == "local"

    @property
    def is_whatsapp_enabled(self) -> bool:
        return bool(self.openwa_api_key and self.openwa_webhook_secret)


settings = Settings()
