from sqlalchemy.orm import Session as DbSession

from app.kernel.models import AuditLog


def write_audit_log(
    db: DbSession,
    actor: str,
    action: str,
    entity: str | None = None,
    entity_id: str | None = None,
    meta: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    log = AuditLog(
        actor=actor,
        action=action,
        entity=entity,
        entity_id=entity_id,
        meta=meta,
        ip_address=ip_address,
    )
    db.add(log)
    db.commit()
    return log
