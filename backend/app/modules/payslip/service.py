from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session as DbSession

from app.kernel.integration import EmployeeDirectoryAdapter, CompanyProfileAdapter
from app.kernel.models import Payslip, PayslipLine, PayslipDelivery, AuditLog
from app.modules.payslip.calculations import calculate_payslip
from app.modules.payslip.schemas import PayslipCreate


class PayslipService:
    def __init__(self, db: DbSession):
        self.db = db
        self.employees = EmployeeDirectoryAdapter(db)
        self.company = CompanyProfileAdapter(db)

    def create_payslip(self, data: PayslipCreate) -> dict:
        calc = calculate_payslip(data.basic, data.other_allowances, [Decimal(str(d["amount"])) for d in data.deduction_lines])
        emp_data = self.employees.get_employee(data.employee_code)
        comp_data = self.company.get_letterhead()
        snapshot = {
            "employee": {"name": data.employee_name or (emp_data["name"] if emp_data else ""), "designation": data.designation or (emp_data["designation"] if emp_data else ""), "date_of_joining": str(data.date_of_joining) if data.date_of_joining else (emp_data.get("date_of_joining") if emp_data else None), "aadhaar": data.aadhaar},
            "company": comp_data,
        }
        payslip = Payslip(
            employee_code=data.employee_code,
            month=data.month,
            status="draft",
            snapshot=snapshot,
            total_working_days=data.total_working_days,
            days_paid=data.days_paid,
            gross=calc["gross"],
            total_deductions=calc["total_deductions"],
            net=calc["net"],
            net_in_words=calc["net_in_words"],
            issued_on=data.date_of_issue or date.today(),
        )
        self.db.add(payslip)
        self.db.flush()
        for d in data.deduction_lines:
            self.db.add(PayslipLine(payslip_id=payslip.id, kind="deduction", label=d["label"], amount=Decimal(str(d["amount"]))))
        self.db.add(PayslipLine(payslip_id=payslip.id, kind="earning", label="Basic", amount=data.basic))
        if data.other_allowances:
            self.db.add(PayslipLine(payslip_id=payslip.id, kind="earning", label="Other Allowances", amount=data.other_allowances))
        self.db.commit()
        return self._to_dict(payslip)

    def get_payslip(self, payslip_id: str) -> Optional[dict]:
        p = self.db.query(Payslip).filter(Payslip.id == payslip_id).first()
        return self._to_dict(p) if p else None

    def list_payslips(self, month: Optional[str] = None, status: Optional[str] = None, skip: int = 0, limit: int = 50) -> list[dict]:
        q = self.db.query(Payslip)
        if month:
            q = q.filter(Payslip.month == month)
        if status:
            q = q.filter(Payslip.status == status)
        return [self._to_dict(p) for p in q.order_by(Payslip.created_at.desc()).offset(skip).limit(limit).all()]

    def update_status(self, payslip_id: str, status: str) -> Optional[dict]:
        p = self.db.query(Payslip).filter(Payslip.id == payslip_id).first()
        if not p:
            return None
        if status == "sent" and p.status == "generated":
            p.status = status
        elif status == "generated" and p.status == "draft":
            p.status = status
        else:
            return None
        self.db.commit()
        return self._to_dict(p)

    def _to_dict(self, p: Payslip) -> dict:
        lines = self.db.query(PayslipLine).filter(PayslipLine.payslip_id == p.id).all()
        return {
            "id": p.id,
            "employee_code": p.employee_code,
            "month": p.month,
            "revision": p.revision,
            "status": p.status,
            "gross": float(p.gross) if p.gross else 0,
            "total_deductions": float(p.total_deductions) if p.total_deductions else 0,
            "net": float(p.net) if p.net else 0,
            "net_in_words": p.net_in_words,
            "issued_on": str(p.issued_on) if p.issued_on else None,
            "lines": [{"kind": l.kind, "label": l.label, "amount": float(l.amount)} for l in lines],
        }