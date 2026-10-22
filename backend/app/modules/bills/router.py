"""Bills module API — read paths for the bills ledger (Phase 1 fills write/OCR)."""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.db import get_db
from app.core.errors import AppError
from app.core.money import Money
from app.core.security import require_user
from app.kernel import models

router = APIRouter(prefix="/api/v1/bills", tags=["bills"])


class BillItemOut(BaseModel):
    description: str | None
    amount: Money | None = None


class BillSummaryOut(BaseModel):
    """List projection: no item lines, to keep the list payload small."""

    id: str
    serial: str | None
    vendor: str | None
    total: Money | None = None
    review_state: str
    source: str


class BillOut(BillSummaryOut):
    """One bill with its item lines."""

    items: list[BillItemOut] = []


@router.get("", response_model=list[BillSummaryOut])
def list_bills(
    db: Annotated[DbSession, Depends(get_db)],
    _user: Annotated[models.User, Depends(require_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict[str, Any]]:
    """Paginated bills list, newest first."""
    bills = list(
        db.scalars(
            select(models.Bill).order_by(models.Bill.created_at.desc()).offset(skip).limit(limit)
        ).all()
    )
    return [
        {
            "id": b.id,
            "serial": b.serial,
            "vendor": b.vendor,
            "total": b.total,
            "review_state": b.review_state,
            "source": b.source,
        }
        for b in bills
    ]


@router.get("/{bill_id}", response_model=BillOut)
def get_bill(
    bill_id: str,
    db: Annotated[DbSession, Depends(get_db)],
    _user: Annotated[models.User, Depends(require_user)],
) -> dict[str, Any]:
    """One bill with its items, 404 when missing."""
    bill = db.get(models.Bill, bill_id)
    if not bill:
        raise AppError(404, "not_found", "Bill not found")
    items = list(
        db.scalars(select(models.BillItem).where(models.BillItem.bill_id == bill_id)).all()
    )
    return {
        "id": bill.id,
        "serial": bill.serial,
        "vendor": bill.vendor,
        "total": bill.total,
        "review_state": bill.review_state,
        "source": bill.source,
        "items": [{"description": i.description, "amount": i.amount} for i in items],
    }
