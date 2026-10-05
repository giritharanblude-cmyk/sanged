import hashlib

from sqlalchemy.orm import Session as DbSession

from app.kernel.models import File


def store_file_record(
    db: DbSession, data: bytes, mime: str, storage_key: str, uploaded_by: str | None = None
) -> dict:
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
