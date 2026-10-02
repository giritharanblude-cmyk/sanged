from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession
from app.core.db import get_db
from app.kernel.auth import get_current_user
from app.kernel.models import User, Employee, EmployeeDocument, AuditLog

router = APIRouter(prefix="/api/v1/employees", tags=["employees"])


class EmployeeCreate(BaseModel):
    employee_code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    designation: str = ""
    email: str = ""
    contact_no: str = ""
    salary: float = 0


@router.get("/employees")
def list_employees(skip: int = Query(0), limit: int = Query(50), db: DbSession = Depends(get_db), user: User = Depends(get_current_user)):
    emps = db.query(Employee).filter(Employee.deleted_at.is_(None)).order_by(Employee.name).offset(skip).limit(limit).all()
    return [{"id": e.id, "code": e.employee_code, "name": e.name, "designation": e.designation, "email": e.email} for e in emps]


@router.post("/employees")
def create_employee(data: EmployeeCreate, db: DbSession = Depends(get_db), user: User = Depends(get_current_user)):
    emp = Employee(employee_code=data.employee_code, name=data.name, designation=data.designation, email=data.email, contact_no=data.contact_no, salary=data.salary)
    db.add(emp)
    log = AuditLog(actor=user.username, action="create", entity="employee", entity_id=emp.id)
    db.add(log)
    db.commit()
    return {"id": emp.id, "name": emp.name}


@router.get("/employees/{employee_id}")
def get_employee(employee_id: str, db: DbSession = Depends(get_db), user: User = Depends(get_current_user)):
    emp = db.query(Employee).filter(Employee.id == employee_id, Employee.deleted_at.is_(None)).first()
    if not emp:
        from app.core.errors import AppError
        raise AppError(404, "not_found", "Employee not found")
    return {"id": emp.id, "code": emp.employee_code, "name": emp.name, "designation": emp.designation, "email": emp.email, "salary": float(emp.salary) if emp.salary else 0}


@router.delete("/employees/{employee_id}")
def delete_employee(employee_id: str, db: DbSession = Depends(get_db), user: User = Depends(get_current_user)):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        from app.core.errors import AppError
        raise AppError(404, "not_found", "Employee not found")
    emp.deleted_at = datetime.now(timezone.utc)
    log = AuditLog(actor=user.username, action="delete", entity="employee", entity_id=emp.id)
    db.add(log)
    db.commit()
    return {"message": "Employee deleted"}