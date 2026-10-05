from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DbSession

from app.core.db import get_db
from app.kernel.auth import get_current_user
from app.kernel.models import User
from app.modules.payslip.schemas import PayslipCreate
from app.modules.payslip.service import PayslipService

router = APIRouter(prefix="/api/v1/payslip", tags=["payslip"])


@router.post("/payslips")
def create_payslip(data: PayslipCreate, db: DbSession = Depends(get_db), user: User = Depends(get_current_user)):
    svc = PayslipService(db)
    return svc.create_payslip(data)


@router.get("/payslips/{payslip_id}")
def get_payslip(payslip_id: str, db: DbSession = Depends(get_db), user: User = Depends(get_current_user)):
    svc = PayslipService(db)
    result = svc.get_payslip(payslip_id)
    if not result:
        from app.core.errors import AppError
        raise AppError(404, "not_found", "Payslip not found")
    return result


@router.get("/payslips")
def list_payslips(month: str | None = Query(None), status: str | None = Query(None), skip: int = Query(0), limit: int = Query(50), db: DbSession = Depends(get_db), user: User = Depends(get_current_user)):
    svc = PayslipService(db)
    return svc.list_payslips(month, status, skip, limit)


@router.post("/payslips/{payslip_id}/generate")
def generate_payslip(payslip_id: str, db: DbSession = Depends(get_db), user: User = Depends(get_current_user)):
    svc = PayslipService(db)
    result = svc.update_status(payslip_id, "generated")
    if not result:
        from app.core.errors import AppError
        raise AppError(400, "invalid_status", "Cannot generate payslip")
    return result


@router.post("/payslips/{payslip_id}/send")
def send_payslip(payslip_id: str, db: DbSession = Depends(get_db), user: User = Depends(get_current_user)):
    svc = PayslipService(db)
    result = svc.update_status(payslip_id, "sent")
    if not result:
        from app.core.errors import AppError
        raise AppError(400, "invalid_status", "Cannot send payslip")
    return result