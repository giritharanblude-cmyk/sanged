"""Integration adapters connecting modules"""
from sqlalchemy.orm import Session as DbSession
from app.kernel.models import Employee, CompanyProfile


class EmployeeDirectoryAdapter:
    def __init__(self, db: DbSession):
        self.db = db

    def get_employee(self, employee_code: str) -> dict | None:
        emp = self.db.query(Employee).filter(Employee.employee_code == employee_code, Employee.deleted_at.is_(None)).first()
        if not emp:
            return None
        return {"id": emp.id, "name": emp.name, "designation": emp.designation, "date_of_joining": str(emp.date_of_joining) if emp.date_of_joining else None, "aadhaar_last4": emp.aadhaar_last4, "payment_mode": emp.payment_mode}

    def list_employees(self) -> list[dict]:
        return [{"id": e.id, "code": e.employee_code, "name": e.name} for e in self.db.query(Employee).filter(Employee.deleted_at.is_(None)).all()]


class CompanyProfileAdapter:
    def __init__(self, db: DbSession):
        self.db = db

    def get_profile(self) -> dict:
        profile = self.db.query(CompanyProfile).first()
        if not profile:
            return {"legal_name": "", "address": "", "phone": "", "email": "", "website": "", "signatory": "", "pf_applicable": True}
        return {"legal_name": profile.legal_name, "address": profile.address, "phone": profile.phone, "email": profile.email, "website": profile.website, "signatory": profile.signatory, "pf_applicable": profile.pf_applicable}

    def get_letterhead(self) -> dict:
        p = self.get_profile()
        return {"name": p["legal_name"], "address": p["address"], "phone": p["phone"], "email": p["email"], "website": p["website"]}

    def get_signatory(self) -> str:
        return self.get_profile().get("signatory", "")

    def is_pf_applicable(self) -> bool:
        return self.get_profile().get("pf_applicable", True)