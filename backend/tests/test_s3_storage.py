"""Live SeaweedFS checks for the S3 adapter and required API features."""

from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import httpx
import pytest

from app.kernel.files import S3FileStorage, create_s3_client, probe_storage


@pytest.fixture
def seaweed_bucket() -> Iterator[tuple[Any, str]]:
    client = create_s3_client()
    bucket = f"sangad-test-{uuid4().hex}"
    client.create_bucket(Bucket=bucket)
    try:
        yield client, bucket
    finally:
        versions = client.list_object_versions(Bucket=bucket)
        for version in versions.get("Versions", []):
            client.delete_object(
                Bucket=bucket,
                Key=version["Key"],
                VersionId=version["VersionId"],
            )
        for marker in versions.get("DeleteMarkers", []):
            client.delete_object(
                Bucket=bucket,
                Key=marker["Key"],
                VersionId=marker["VersionId"],
            )
        client.delete_bucket(Bucket=bucket)


def test_s3_adapter_roundtrip_and_presigned_download(
    seaweed_bucket: tuple[Any, str],
) -> None:
    client, bucket = seaweed_bucket
    storage = S3FileStorage(bucket=bucket, client=client)
    payload = b"phase zero seaweedfs object"
    key = "invoices/2026/example.bin"

    assert storage.upload(payload, "application/octet-stream", key) == key
    assert storage.download(key) == payload
    url = storage.presigned_download_url(key, expires_in=60)
    response = httpx.get(url, timeout=10)
    response.raise_for_status()
    assert response.content == payload

    storage.delete(key)
    assert storage.download(key) is None
    probe_storage()


def test_seaweedfs_supports_s3_bucket_versioning(
    seaweed_bucket: tuple[Any, str],
) -> None:
    client, bucket = seaweed_bucket
    key = "versioned/object.bin"

    client.put_bucket_versioning(
        Bucket=bucket,
        VersioningConfiguration={"Status": "Enabled"},
    )
    assert client.get_bucket_versioning(Bucket=bucket)["Status"] == "Enabled"

    first = client.put_object(Bucket=bucket, Key=key, Body=b"version one")
    second = client.put_object(Bucket=bucket, Key=key, Body=b"version two")

    assert first.get("VersionId")
    assert second.get("VersionId")
    assert first["VersionId"] != second["VersionId"]
    first_body = client.get_object(
        Bucket=bucket,
        Key=key,
        VersionId=first["VersionId"],
    )["Body"]
    second_body = client.get_object(
        Bucket=bucket,
        Key=key,
        VersionId=second["VersionId"],
    )["Body"]
    try:
        assert first_body.read() == b"version one"
        assert second_body.read() == b"version two"
    finally:
        first_body.close()
        second_body.close()
