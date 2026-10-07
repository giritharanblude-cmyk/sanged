"""Bills module API — read paths for the bills ledger (Phase 1 fills write/OCR)."""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import require_user
from app.kernel import models

router = APIRouter(prefix="/api/v1/bills", tags=["bills"])


class BillItemOut(BaseModel):
    description: str | None
    amount: float


class BillOut(BaseModel):
    id: str
    serial: str | None
    vendor: str | None
    total: float
    review_state: str
    source: str
    items: list[BillItemOut] = []


@router.get("/bills")
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
            "total": float(b.total) if b.total else 0.0,
            "review_state": b.review_state,
            "source": b.source,
        }
        for b in bills
    ]


@router.get("/bills/{bill_id}")
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
        "total": float(bill.total) if bill.total else 0.0,
        "review_state": bill.review_state,
        "items": [
            {"description": i.description, "amount": float(i.amount) if i.amount else 0.0}
            for i in items
        ],
    }
