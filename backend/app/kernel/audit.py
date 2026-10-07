"""Append-only audit log helper (R-12, NFR-AUD-01)."""
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session as DbSession

from app.kernel.models import AuditLog


@dataclass
class AuditContext:
    """Everything that identifies who did what, from where."""

    actor: str
    action: str
    entity: str | None = None
    entity_id: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    ip_address: str | None = None


def write_audit_log(db: DbSession, ctx: AuditContext) -> AuditLog:
    """Insert one audit row and commit. Callers own the surrounding transaction."""
    log = AuditLog(
        actor=ctx.actor,
        action=ctx.action,
        entity=ctx.entity,
        entity_id=ctx.entity_id,
        meta=ctx.meta or None,
        ip_address=ctx.ip_address,
    )
    db.add(log)
    db.commit()
    return log
