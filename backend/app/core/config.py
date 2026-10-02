from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    app_env: str = "local"
    debug: bool = False
    database_url: str = "postgresql://sangad:sangad@localhost:5432/sangad"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me-in-production"
    allowed_hosts: List[str] = ["sangad.localhost"]
    cookie_secure: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()