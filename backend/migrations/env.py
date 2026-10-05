import sys
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Alembic loads env.py without the project root on sys.path, so `app` is only
# importable if we add the backend directory (the parent of migrations/) here.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.kernel.models import Base  # noqa: E402

config = context.config
target_metadata = Base.metadata

# Prefer DATABASE_URL over the placeholder baked into alembic.ini, otherwise
# migrations inside the container would target localhost instead of postgres.
if settings.database_url:
    config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()