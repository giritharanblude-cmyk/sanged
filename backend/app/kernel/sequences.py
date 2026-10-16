from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session as DbSession

from app.kernel.models import NumberSequence

FY_START_MONTH = 4  # April, per C-04 (financial year Apr-Mar)


def next_serial(db: DbSession, series: str, fy: str | None = None) -> str:
    now = datetime.now(UTC)
    year = now.year
    fy = fy or (
        f"{year % 100}{(year + 1) % 100}"
        if now.month >= FY_START_MONTH
        else f"{(year - 1) % 100}{year % 100}"
    )
    statement = (
        insert(NumberSequence)
        .values(series=series, fy=fy, last_value=1)
        .on_conflict_do_update(
            index_elements=[NumberSequence.series, NumberSequence.fy],
            set_={"last_value": NumberSequence.last_value + 1},
        )
        .returning(NumberSequence.last_value)
    )
    last_value = db.execute(statement).scalar_one()
    db.commit()
    return f"{series}-{fy}-{last_value:06d}"
