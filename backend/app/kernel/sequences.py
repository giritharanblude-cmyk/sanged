from datetime import UTC, datetime

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
    seq = (
        db.query(NumberSequence)
        .filter(NumberSequence.series == series, NumberSequence.fy == fy)
        .with_for_update()
        .first()
    )
    if not seq:
        seq = NumberSequence(series=series, fy=fy, last_value=0)
        db.add(seq)
    seq.last_value += 1
    db.commit()
    return f"{series}-{fy}-{seq.last_value:06d}"
