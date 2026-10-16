"""Inventory module API — stock items with ledger-derived quantity (F-INV-*)."""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Integer, case, cast, func, select
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
    """List a page and aggregate ledger quantities in the database."""
    items = list(
        db.scalars(
            select(models.StockItem)
            .order_by(models.StockItem.name)
            .offset(skip)
            .limit(limit)
        ).all()
    )
    quantity = cast(
        func.coalesce(
            func.sum(
                case(
                    (models.StockMovement.kind == "in", models.StockMovement.qty),
                    (models.StockMovement.kind == "out", -models.StockMovement.qty),
                    else_=models.StockMovement.qty,
                )
            ),
            0,
        ),
        Integer,
    )
    quantity_rows = db.execute(
        select(models.StockMovement.item_id, quantity)
        .group_by(models.StockMovement.item_id)
    ).all()
    quantities = {item_id: int(total) for item_id, total in quantity_rows}

    return [
        {
            "id": item.id,
            "sku": item.sku,
            "name": item.name,
            "category": item.category or "",
            "unit": item.unit or "",
            "quantity": quantities.get(item.id, 0),
            "reorder_level": item.reorder_level,
            "unit_cost": float(item.unit_cost) if item.unit_cost else 0.0,
        }
        for item in items
    ]
