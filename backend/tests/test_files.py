"""File storage readiness checks."""

from pathlib import Path

import pytest

from app.core.config import settings
from app.kernel.files import FilesystemStorage, probe_storage


def test_filesystem_probe_writes_reads_and_removes_probe_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(settings, "storage_backend", "filesystem")
    monkeypatch.setattr(settings, "storage_path", str(tmp_path))

    probe_storage()

    assert list(tmp_path.iterdir()) == []


def test_filesystem_adapter_upload_download_and_delete(tmp_path: Path) -> None:
    storage = FilesystemStorage(tmp_path)
    payload = b"phase zero filesystem object"
    key = "invoices/2026/example.bin"

    assert storage.upload(payload, "application/octet-stream", key) == key
    assert storage.download(key) == payload

    storage.delete(key)

    assert storage.download(key) is None


@pytest.mark.parametrize("key", ["../escape", "/absolute", r"folder\\escape"])
def test_filesystem_adapter_rejects_unsafe_keys(tmp_path: Path, key: str) -> None:
    storage = FilesystemStorage(tmp_path)

    with pytest.raises(ValueError, match="relative POSIX path"):
        storage.upload(b"data", "application/octet-stream", key)
