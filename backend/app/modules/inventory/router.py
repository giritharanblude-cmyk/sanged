from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DbSession
from app.core.db import get_db
from app.kernel.auth import get_current_user
from app.kernel.models import User, StockItem, StockMovement

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


@router.get("/items")
def list_items(skip: int = Query(0), limit: int = Query(50), db: DbSession = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.query(StockItem).order_by(StockItem.name).offset(skip).limit(limit).all()
    result = []
    for item in items:
        qty = db.query(StockMovement).filter(StockMovement.item_id == item.id).with_entities(db.query(StockMovement).filter(StockMovement.kind == "in").statement.union_all(
            db.query(-StockMovement.qty).filter(StockMovement.kind == "out").statement
        )).all()
        total_qty = sum((m.qty if m.kind == "in" else -m.qty) for m in db.query(StockMovement).filter(StockMovement.item_id == item.id).all())
        result.append({"id": item.id, "sku": item.sku, "name": item.name, "quantity": total_qty, "reorder_level": item.reorder_level, "unit_cost": float(item.unit_cost) if item.unit_cost else 0})
    return result