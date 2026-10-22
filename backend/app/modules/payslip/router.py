"""Payslip module API (T-101, T-103): create/list/get + lifecycle endpoints."""
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DbSession

from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import require_user
from app.kernel import models
from app.modules.payslip.schemas import PayslipCreate, PayslipOut
from app.modules.payslip.service import PayslipService

router = APIRouter(prefix="/api/v1/payslip", tags=["payslip"])


@router.post("/payslips", response_model=PayslipOut)
def create_payslip(
    data: PayslipCreate,
    db: Annotated[DbSession, Depends(get_db)],
    _user: Annotated[models.User, Depends(require_user)],
) -> dict[str, Any]:
    """Manual entry (F-PAY-02). Import path arrives with the wizard in Phase 1."""
    return PayslipService(db).create_payslip(data)


@router.get("/payslips", response_model=list[PayslipOut])
def list_payslips(
    db: Annotated[DbSession, Depends(get_db)],
    _user: Annotated[models.User, Depends(require_user)],
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    status: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict[str, Any]]:
    """Payroll list backing the payroll screen (F-PAY-08)."""
    return PayslipService(db).list_payslips(month, status, skip, limit)


@router.get("/payslips/{payslip_id}", response_model=PayslipOut)
def get_payslip(
    payslip_id: str,
    db: Annotated[DbSession, Depends(get_db)],
    _user: Annotated[models.User, Depends(require_user)],
) -> dict[str, Any]:
    """One payslip with lines (F-PAY-04 preview data)."""
    result = PayslipService(db).get_payslip(payslip_id)
    if not result:
        raise AppError(404, "not_found", "Payslip not found")
    return result


@router.post("/payslips/{payslip_id}/generate", response_model=PayslipOut)
def generate_payslip(
    payslip_id: str,
    db: Annotated[DbSession, Depends(get_db)],
    _user: Annotated[models.User, Depends(require_user)],
) -> dict[str, Any]:
    """Lifecycle: draft -> generated (F-PAY-13)."""
    result = PayslipService(db).update_status(payslip_id, "generated")
    if not result:
        raise AppError(400, "invalid_status", "Cannot generate payslip from its current status")
    return result


@router.post("/payslips/{payslip_id}/send", response_model=PayslipOut)
def send_payslip(
    payslip_id: str,
    db: Annotated[DbSession, Depends(get_db)],
    _user: Annotated[models.User, Depends(require_user)],
) -> dict[str, Any]:
    """Lifecycle: generated -> sent (F-PAY-07 wire-up lands in Phase 1)."""
    result = PayslipService(db).update_status(payslip_id, "sent")
    if not result:
        raise AppError(400, "invalid_status", "Cannot send payslip from its current status")
    return result
