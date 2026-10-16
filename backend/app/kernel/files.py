"""File storage adapters and readiness probes (T-005, T-010)."""

from __future__ import annotations

import hashlib
import secrets
from pathlib import Path, PurePosixPath
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.kernel.models import File
from app.kernel.ports import FileStoragePort

HTTP_NOT_FOUND = 404
MAX_PRESIGNED_URL_SECONDS = 7 * 24 * 60 * 60


class FilesystemStorage:
    """Filesystem implementation used by unit tests and local fallback mode."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        relative = PurePosixPath(key)
        if (
            not key
            or relative.is_absolute()
            or not relative.parts
            or "\\" in key
            or "\x00" in key
            or ":" in key
            or any(part in {".", ".."} for part in relative.parts)
        ):
            raise ValueError("Storage key must be a relative POSIX path")
        path = (self.root / Path(*relative.parts)).resolve()
        if self.root not in path.parents:
            raise ValueError("Storage key escapes the configured storage root")
        return path

    def upload(self, data: bytes, mime: str, key: str) -> str:
        del mime
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def download(self, key: str) -> bytes | None:
        path = self._path(key)
        try:
            return path.read_bytes()
        except FileNotFoundError:
            return None

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


def create_s3_client() -> Any:
    """Create an S3 client with the configured endpoint and addressing mode."""
    if not settings.s3_endpoint_url:
        raise ValueError("S3_ENDPOINT_URL is required when STORAGE_BACKEND=s3")
    if bool(settings.s3_access_key) != bool(settings.s3_secret_key):
        raise ValueError("S3_ACCESS_KEY and S3_SECRET_KEY must be set together")
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key or None,
        aws_secret_access_key=settings.s3_secret_key or None,
        region_name="us-east-1",
        config=Config(
            s3={
                "addressing_style": (
                    "path" if settings.s3_force_path_style else "virtual"
                )
            }
        ),
    )


class S3FileStorage:
    """S3-compatible object storage implementation for application files."""

    def __init__(self, bucket: str | None = None, client: Any | None = None) -> None:
        self.bucket = bucket or settings.s3_bucket_files
        if not self.bucket:
            raise ValueError("S3_BUCKET_FILES must not be empty")
        self.client = client if client is not None else create_s3_client()

    def upload(self, data: bytes, mime: str, key: str) -> str:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=mime,
        )
        return key

    def download(self, key: str) -> bytes | None:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            error = exc.response.get("Error", {})
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if (
                error.get("Code") in {"NoSuchKey", "NotFound", "404"}
                or status == HTTP_NOT_FOUND
            ):
                return None
            raise
        body = response["Body"]
        try:
            data = body.read()
            if not isinstance(data, bytes):
                raise TypeError("S3 object body did not return bytes")
            return data
        finally:
            body.close()

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def presigned_download_url(self, key: str, expires_in: int = 300) -> str:
        if not 1 <= expires_in <= MAX_PRESIGNED_URL_SECONDS:
            raise ValueError(
                "Presigned URL expiry must be between 1 and "
                f"{MAX_PRESIGNED_URL_SECONDS} seconds"
            )
        return str(
            self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )
        )


def get_file_storage() -> FileStoragePort:
    if settings.storage_backend == "filesystem":
        return FilesystemStorage(settings.storage_path)
    return S3FileStorage()


def probe_storage() -> None:
    """Write, read, and remove a unique object to verify storage readiness."""
    storage = get_file_storage()
    key = f"health-probe-{secrets.token_hex(16)}"
    payload = f"sangad-storage-ready:{secrets.token_hex(16)}".encode()
    try:
        storage.upload(payload, "application/octet-stream", key)
        if storage.download(key) != payload:
            raise OSError("Storage probe returned unexpected data")
    finally:
        storage.delete(key)


def store_file_record(
    db: DbSession, data: bytes, mime: str, storage_key: str, uploaded_by: str | None = None
) -> dict[str, object]:
    sha256 = hashlib.sha256(data).hexdigest()
    existing = db.query(File).filter(File.sha256 == sha256).first()
    if existing:
        return {"id": existing.id, "sha256": sha256, "duplicate": True}
    file = File(
        sha256=sha256, mime=mime, size=len(data), storage_key=storage_key, uploaded_by=uploaded_by
    )
    db.add(file)
    db.commit()
    return {"id": file.id, "sha256": sha256, "duplicate": False}


def get_file(db: DbSession, file_id: str) -> File | None:
    return db.query(File).filter(File.id == file_id).first()
