from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DbSession
from app.core.db import get_db
from app.kernel.auth import get_current_user
from app.kernel.models import User, Bill, BillItem

router = APIRouter(prefix="/api/v1/bills", tags=["bills"])


@router.get("/bills")
def list_bills(skip: int = Query(0), limit: int = Query(50), db: DbSession = Depends(get_db), user: User = Depends(get_current_user)):
    bills = db.query(Bill).order_by(Bill.created_at.desc()).offset(skip).limit(limit).all()
    return [{"id": b.id, "serial": b.serial, "vendor": b.vendor, "total": float(b.total) if b.total else 0, "review_state": b.review_state, "source": b.source} for b in bills]


@router.get("/bills/{bill_id}")
def get_bill(bill_id: str, db: DbSession = Depends(get_db), user: User = Depends(get_current_user)):
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        from app.core.errors import AppError
        raise AppError(404, "not_found", "Bill not found")
    items = db.query(BillItem).filter(BillItem.bill_id == bill_id).all()
    return {"id": bill.id, "serial": bill.serial, "vendor": bill.vendor, "total": float(bill.total) if bill.total else 0, "review_state": bill.review_state, "items": [{"description": i.description, "amount": float(i.amount) if i.amount else 0} for i in items]}