"""Integration adapters connecting modules through ports (D-ARCH-01)."""
from typing import Any

from sqlalchemy.orm import Session as DbSession

from app.kernel.models import CompanyProfile, Employee


class EmployeeDirectoryAdapter:
    """EmployeeDirectoryPort backed by the employees tables (T-601)."""

    def __init__(self, db: DbSession) -> None:
        self.db = db

    def get_employee(self, employee_code: str) -> dict[str, Any] | None:
        emp = (
            self.db.query(Employee)
            .filter(
                Employee.employee_code == employee_code,
                Employee.deleted_at.is_(None),
            )
            .first()
        )
        if not emp:
            return None
        return {
            "id": emp.id,
            "name": emp.name,
            "designation": emp.designation,
            "date_of_joining": str(emp.date_of_joining) if emp.date_of_joining else None,
            "aadhaar_last4": emp.aadhaar_last4,
            "payment_mode": emp.payment_mode,
        }

    def list_employees(self) -> list[dict[str, Any]]:
        rows = (
            self.db.query(Employee)
            .filter(Employee.deleted_at.is_(None))
            .order_by(Employee.name)
            .all()
        )
        return [
            {"id": e.id, "code": e.employee_code, "name": e.name} for e in rows
        ]


class CompanyProfileAdapter:
    """CompanyProfilePort backed by the company_profile row (T-601)."""

    def __init__(self, db: DbSession) -> None:
        self.db = db

    def get_profile(self) -> dict[str, Any]:
        profile = self.db.query(CompanyProfile).first()
        if not profile:
            return {
                "legal_name": "",
                "address": "",
                "phone": "",
                "email": "",
                "website": "",
                "signatory": "",
                "pf_applicable": True,
            }
        return {
            "legal_name": profile.legal_name,
            "address": profile.address,
            "phone": profile.phone,
            "email": profile.email,
            "website": profile.website,
            "signatory": profile.signatory,
            "pf_applicable": profile.pf_applicable,
        }

    def get_letterhead(self) -> dict[str, Any]:
        p = self.get_profile()
        return {
            "name": p["legal_name"],
            "address": p["address"],
            "phone": p["phone"],
            "email": p["email"],
            "website": p["website"],
        }

    def get_signatory(self) -> str:
        value = self.get_profile()["signatory"]
        return str(value) if value is not None else ""

    def is_pf_applicable(self) -> bool:
        value = self.get_profile()["pf_applicable"]
        return bool(value)
