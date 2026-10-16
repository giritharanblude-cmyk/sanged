"""Grant runtime access while keeping audit records append-only."""

import os

from alembic import op
from sqlalchemy import text

revision: str = "3c5f09c807ab"
down_revision: str | None = "b7e7fa3720b4"
branch_labels: str | None = None
depends_on: str | None = None


def _quoted_identifier(value: str) -> str:
    preparer = op.get_bind().dialect.identifier_preparer
    return str(preparer.quote(value))


def _roles() -> tuple[str, str]:
    app_role = os.environ.get("APP_DB_USER")
    if not app_role:
        raise RuntimeError("APP_DB_USER is required to grant runtime database access")
    owner_role = str(op.get_bind().execute(text("SELECT current_user")).scalar_one())
    return _quoted_identifier(app_role), _quoted_identifier(owner_role)


def upgrade() -> None:
    app_role, owner_role = _roles()
    op.execute(f"GRANT USAGE ON SCHEMA public TO {app_role}")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public "
        f"TO {app_role}"
    )
    op.execute(f"REVOKE UPDATE, DELETE ON TABLE public.audit_log FROM {app_role}")
    op.execute(f"REVOKE ALL PRIVILEGES ON TABLE public.alembic_version FROM {app_role}")
    op.execute(
        "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public "
        f"TO {app_role}"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE "
        f"{owner_role} IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE "
        f"ON TABLES TO {app_role}"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE "
        f"{owner_role} IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES "
        f"TO {app_role}"
    )


def downgrade() -> None:
    app_role, owner_role = _roles()
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE "
        f"{owner_role} IN SCHEMA public REVOKE SELECT, INSERT, UPDATE, DELETE "
        f"ON TABLES FROM {app_role}"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE "
        f"{owner_role} IN SCHEMA public REVOKE USAGE, SELECT ON SEQUENCES "
        f"FROM {app_role}"
    )
    op.execute(
        "REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public "
        f"FROM {app_role}"
    )
    op.execute(
        "REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public "
        f"FROM {app_role}"
    )
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {app_role}")
