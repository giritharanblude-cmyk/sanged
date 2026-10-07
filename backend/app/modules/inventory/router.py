"""Inventory module API — stock items with ledger-derived quantity (F-INV-*)."""
from collections import defaultdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.db import get_db
from app.core.security import require_user
from app.kernel import models

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


@router.get("/items")
def list_items(
    db: Annotated[DbSession, Depends(get_db)],
    _user: Annotated[models.User, Depends(require_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict[str, Any]]:
    """One query for items, one for movements; quantity sums per item in Python
    (F-INV-03: quantity derives from the movement ledger)."""
    items = list(
        db.scalars(
            select(models.StockItem).order_by(models.StockItem.name).offset(skip).limit(limit)
        ).all()
    )
    movements = list(
        db.execute(
            select(
                models.StockMovement.item_id,
                models.StockMovement.kind,
                models.StockMovement.qty,
            )
        ).all()
    )
    qty_by_item: dict[str, int] = defaultdict(int)
    for item_id, kind, qty in movements:
        qty_by_item[item_id] += qty if kind == "in" else -qty

    return [
        {
            "id": item.id,
            "sku": item.sku,
            "name": item.name,
            "category": item.category or "",
            "unit": item.unit or "",
            "quantity": qty_by_item.get(item.id, 0),
            "reorder_level": item.reorder_level,
            "unit_cost": float(item.unit_cost) if item.unit_cost else 0.0,
        }
        for item in items
    ]
