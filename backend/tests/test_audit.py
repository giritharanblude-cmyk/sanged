"""PostgreSQL permission tests for the append-only audit log role."""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError

from app.core.db import SessionLocal
from app.kernel.models import AuditLog


def _assert_permission_denied(error: pytest.ExceptionInfo[DBAPIError]) -> None:
    assert getattr(error.value.orig, "pgcode", None) == "42501"


def test_runtime_role_can_insert_but_cannot_update_or_delete_audit_rows(
    db_engine: Engine,
    app_role_engine: Engine,
) -> None:
    del db_engine
    owner_row_id = str(uuid4())
    app_row_id = str(uuid4())
    try:
        with SessionLocal() as owner_session:
            owner_session.add(
                AuditLog(
                    id=owner_row_id,
                    actor="test",
                    action="permission_test",
                    entity="test",
                    entity_id=owner_row_id,
                )
            )
            owner_session.commit()

        with app_role_engine.begin() as app_connection:
            app_connection.execute(
                text("INSERT INTO audit_log (id, actor, action) VALUES (:id, :actor, :action)"),
                {"id": app_row_id, "actor": "app", "action": "insert_test"},
            )

        with pytest.raises(DBAPIError) as update_error, app_role_engine.begin() as app_connection:
            app_connection.execute(
                text("UPDATE audit_log SET action = 'changed' WHERE id = :id"),
                {"id": owner_row_id},
            )
        _assert_permission_denied(update_error)

        with pytest.raises(DBAPIError) as delete_error, app_role_engine.begin() as app_connection:
            app_connection.execute(
                text("DELETE FROM audit_log WHERE id = :id"),
                {"id": owner_row_id},
            )
        _assert_permission_denied(delete_error)
    finally:
        with SessionLocal() as owner_session:
            owner_session.query(AuditLog).filter(
                AuditLog.id.in_([owner_row_id, app_row_id])
            ).delete(synchronize_session=False)
            owner_session.commit()
