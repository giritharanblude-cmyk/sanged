"""The restore drill: a backup that cannot be restored is not a backup.

infra/scripts/restore.sh restores a dump into a scratch database and
compares the row counts of every table with the source. This test runs
exactly that script against the live test database, so the drill that
the operator repeats after a reboot is the same one the build proves.

The script needs pg_dump, pg_restore and psql, which the API image
installs for this purpose.
"""
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

SCRATCH_DB = "sangad_restore_drill_test"
RESTORE_SCRIPT = Path("infra/scripts/restore.sh")


def _script_path() -> Path:
    """Locate infra/scripts/restore.sh."""
    configured = os.environ.get("SANGAD_REPO_ROOT")
    if configured:
        return Path(configured) / RESTORE_SCRIPT
    for candidate in Path(__file__).resolve().parents:
        if (candidate / RESTORE_SCRIPT).is_file():
            return candidate / RESTORE_SCRIPT
    raise RuntimeError(
        "Cannot locate infra/scripts/restore.sh. Set SANGAD_REPO_ROOT to the "
        "repository root."
    )


def _tool(name: str) -> str:
    """The absolute path of a PostgreSQL client tool."""
    path = shutil.which(name)
    assert path, f"{name} is not on the PATH"
    return path


def _run(command: list[str], check: bool = True, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """Run a fixed command, never through a shell.

    Every argument is a literal or a value this test produced itself, so
    there is no untrusted input in the call. Bandit cannot see that, which
    is why the exemption sits on this one helper instead of on every call
    site.
    """
    return subprocess.run(  # noqa: S603
        command, check=check, capture_output=True, text=True, **kwargs
    )


def _pg_url(url: str) -> str:
    """Turn a SQLAlchemy URL into one the PostgreSQL client tools accept."""
    return url.replace("postgresql+psycopg2://", "postgresql://")


def _scratch_url(source_pg: str) -> str:
    """The same connection, pointing at the scratch database."""
    return source_pg.replace(urlparse(source_pg).path.rsplit("/", 1)[-1], SCRATCH_DB)


def _table_counts(url: str) -> dict[str, int]:
    """Row count of every public table, read with psql."""
    tables = _run(
        [
            _tool("psql"),
            url,
            "-At",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name;",
        ]
    ).stdout.split()

    counts: dict[str, int] = {}
    for table in tables:
        # The table name comes from the server's own catalogue, not from
        # anything a user supplied, so interpolating it is safe.
        counted = _run(
            [
                _tool("psql"),
                url,
                "-At",
                "-c",
                f'SELECT count(*) FROM public."{table}";',  # noqa: S608
            ]
        )
        counts[table] = int(counted.stdout.strip())
    return counts


def _drop_scratch(admin_pg: str) -> None:
    _run(
        [
            _tool("psql"),
            admin_pg,
            "-v",
            "ON_ERROR_STOP=1",
            "-q",
            "-c",
            f"DROP DATABASE IF EXISTS {SCRATCH_DB} WITH (FORCE);",
        ],
        check=False,
    )


@pytest.fixture(scope="module")
def postgres_tools() -> None:
    """The PostgreSQL client tools have to be on the PATH."""
    missing = [tool for tool in ("psql", "pg_dump", "pg_restore") if not shutil.which(tool)]
    assert not missing, f"missing PostgreSQL client tools: {missing}"


def test_the_restore_script_restores_into_a_scratch_database(
    db_engine: Engine, postgres_tools: None, tmp_path: Path
) -> None:
    """Dump the database, restore it into a scratch database, compare counts."""
    del postgres_tools
    source_pg = _pg_url(os.environ["TEST_DATABASE_URL"])
    admin_pg = source_pg

    # Put some known rows in the source so the comparison is not empty.
    with db_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (id, username, password_hash, role, email, is_active) "
                "VALUES (:id, 'restore-probe', 'x', 'master', 'restore@sangad.localhost', true) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": "00000000-0000-4000-8000-00000000d411"},
        )

    dump_file = tmp_path / "sangad.dump"
    _run(
        [
            _tool("pg_dump"),
            "--dbname",
            source_pg,
            "--format",
            "custom",
            "--file",
            str(dump_file),
        ]
    )
    assert dump_file.exists()
    assert dump_file.stat().st_size > 0

    before = _table_counts(source_pg)
    assert before, "the source database has no tables"
    assert before.get("users", 0) >= 1

    result = _run(
        [
            "bash",
            str(_script_path()),
            "--dump",
            str(dump_file),
            "--scratch-db",
            SCRATCH_DB,
            "--source-url",
            source_pg,
            "--admin-url",
            admin_pg,
        ],
        check=False,
    )
    assert result.returncode == 0, f"restore.sh failed:\n{result.stdout}\n{result.stderr}"
    assert "PASS" in result.stdout

    # The scratch database really exists and holds the same rows.
    after = _table_counts(_scratch_url(source_pg))
    assert after == before

    # Tidy up: the drill must not leave a database behind.
    _drop_scratch(admin_pg)


def test_the_restore_script_refuses_a_dump_that_does_not_match(
    postgres_tools: None, tmp_path: Path
) -> None:
    """A restore that silently loses rows must fail the drill."""
    del postgres_tools
    source_pg = _pg_url(os.environ["TEST_DATABASE_URL"])
    admin_pg = source_pg

    empty_dump = tmp_path / "empty.sql"
    empty_dump.write_text("-- an empty dump\n", encoding="utf-8")

    result = _run(
        [
            "bash",
            str(_script_path()),
            "--dump",
            str(empty_dump),
            "--scratch-db",
            SCRATCH_DB,
            "--source-url",
            source_pg,
            "--admin-url",
            admin_pg,
        ],
        check=False,
    )
    assert result.returncode != 0
    assert "MISMATCH" in result.stderr or "does not have the same tables" in result.stderr

    _drop_scratch(admin_pg)
