"""PostgreSQL-backed tests for gapless, concurrent serial allocation."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from sqlalchemy import delete
from sqlalchemy.engine import Engine

from app.core.db import SessionLocal
from app.kernel.models import NumberSequence
from app.kernel.sequences import next_serial

SERIAL_COUNT = 100


def test_next_serial_allocates_one_hundred_gapless_values(
    db_engine: Engine,
) -> None:
    database_name = db_engine.url.database
    assert database_name is not None
    assert database_name.endswith("_test")

    series = f"T{uuid4().hex[:12].upper()}"
    financial_year = "TEST26"

    def allocate(_: int) -> str:
        with SessionLocal() as session:
            return next_serial(session, series, financial_year)

    try:
        with ThreadPoolExecutor(max_workers=20) as pool:
            serials = list(pool.map(allocate, range(SERIAL_COUNT)))
        values = [int(serial.rsplit("-", maxsplit=1)[1]) for serial in serials]
        assert len(set(serials)) == SERIAL_COUNT
        assert sorted(values) == list(range(1, SERIAL_COUNT + 1))
    finally:
        with SessionLocal() as cleanup:
            cleanup.execute(
                delete(NumberSequence).where(
                    NumberSequence.series == series,
                    NumberSequence.fy == financial_year,
                )
            )
            cleanup.commit()
