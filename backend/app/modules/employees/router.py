"""Employees module — CRUD API for the Employees module (F-EMP-01..06)."""
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import require_user
from app.kernel.audit import AuditContext, write_audit_log
from app.kernel.models import Employee, User

router = APIRouter(prefix="/api/v1/employees", tags=["employees"])

DbDep = Annotated[DbSession, Depends(get_db)]
UserDep = Annotated[User, Depends(require_user)]


class EmployeeCreate(BaseModel):
    """Payload validation for POST /employees."""

    employee_code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    designation: str = Field(default="", max_length=200)
    email: str = Field(default="", max_length=255)
    contact_no: str = Field(default="", max_length=20)
    salary: float = Field(default=0, ge=0)


class EmployeeOut(BaseModel):
    """Response model for the employee list endpoints."""

    id: str
    code: str
    name: str
    designation: str
    email: str


def _to_out(emp: Employee) -> EmployeeOut:
    return EmployeeOut(
        id=emp.id,
        code=emp.employee_code,
        name=emp.name,
        designation=emp.designation or "",
        email=emp.email or "",
    )


@router.get("/employees")
def list_employees(
    db: DbDep,
    _user: UserDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[EmployeeOut]:
    """List endpoint for F-EMP-06. Correct, paginated, soft-delete aware."""
    stmt = (
        select(Employee)
        .where(Employee.deleted_at.is_(None))
        .order_by(Employee.name)
        .offset(skip)
        .limit(limit)
    )
    emps = list(db.scalars(stmt).all())
    return [_to_out(emp) for emp in emps]


@router.post("/employees")
def create_employee(data: EmployeeCreate, db: DbDep, user: UserDep) -> dict[str, str]:
    """Manual entry (F-EMP-01). duplicate employee_code -> 409 (F-EMP-05)."""
    existing = db.scalar(
        select(func.count()).select_from(Employee).where(
            Employee.employee_code == data.employee_code
        )
    )
    if existing:
        raise AppError(409, "duplicate_employee_code", "employee_code already exists")
    emp = Employee(
        employee_code=data.employee_code,
        name=data.name,
        designation=data.designation,
        email=data.email,
        contact_no=data.contact_no,
        salary=Decimal(str(data.salary)),
    )
    db.add(emp)
    db.flush()
    write_audit_log(
        db,
        AuditContext(actor=user.username, action="create", entity="employee", entity_id=emp.id),
    )
    db.commit()
    return {"id": emp.id, "name": emp.name}


@router.get("/employees/{employee_id}")
def get_employee(employee_id: str, db: DbDep, _user: UserDep) -> dict[str, Any]:
    """One employee, 404 when missing (F-EMP-06)."""
    emp = db.get(Employee, employee_id)
    if not emp or emp.deleted_at is not None:
        raise AppError(404, "not_found", "Employee not found")
    return {
        "id": emp.id,
        "code": emp.employee_code,
        "name": emp.name,
        "designation": emp.designation or "",
        "email": emp.email or "",
        "salary": float(emp.salary) if emp.salary else 0.0,
    }


@router.delete("/employees/{employee_id}")
def delete_employee(employee_id: str, db: DbDep, user: UserDep) -> dict[str, str]:
    """Soft delete only, so payslip history survives (F-EMP-05)."""
    emp = db.get(Employee, employee_id)
    if not emp or emp.deleted_at is not None:
        raise AppError(404, "not_found", "Employee not found")
    emp.deleted_at = datetime.now(UTC)
    write_audit_log(
        db,
        AuditContext(actor=user.username, action="delete", entity="employee", entity_id=emp.id),
    )
    db.commit()
    return {"message": "Employee deleted"}
