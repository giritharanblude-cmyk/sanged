"""Payslip service: create/list/get + lifecycle transitions (T-101..T-106)."""
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.errors import AppError
from app.kernel.integration import CompanyProfileAdapter, EmployeeDirectoryAdapter
from app.kernel.models import AuditLog, Payslip, PayslipLine
from app.modules.payslip.calculations import calculate_payslip
from app.modules.payslip.schemas import PayslipCreate


class PayslipService:
    def __init__(self, db: DbSession) -> None:
        self.db = db
        self.employees = EmployeeDirectoryAdapter(db)
        self.company = CompanyProfileAdapter(db)

    def create_payslip(self, data: PayslipCreate) -> dict[str, Any]:
        calc = calculate_payslip(
            data.basic, data.other_allowances, [d.amount for d in data.deduction_lines]
        )
        emp = self.employees.get_employee(data.employee_code)
        letterhead = self.company.get_letterhead()
        snapshot = {
            "employee": {
                "name": data.employee_name or (emp or {}).get("name", ""),
                "designation": data.designation or (emp or {}).get("designation") or "",
                "date_of_joining": data.date_of_joining.isoformat()
                if data.date_of_joining
                else (emp or {}).get("date_of_joining"),
                "aadhaar": data.aadhaar,
                "payment_mode": data.payment_mode or (emp or {}).get("payment_mode") or "",
            },
            "company": letterhead,
        }
        payslip = Payslip(
            employee_code=data.employee_code,
            month=data.month,
            status="draft",
            snapshot=snapshot,
            total_working_days=data.total_working_days,
            days_paid=data.days_paid,
            gross=Decimal(str(calc["gross"])),
            total_deductions=Decimal(str(calc["total_deductions"])),
            net=Decimal(str(calc["net"])),
            net_in_words=str(calc["net_in_words"]),
            issued_on=data.date_of_issue or datetime.now(UTC).date(),
        )
        self.db.add(payslip)
        self.db.flush()
        for line in data.deduction_lines:
            self.db.add(
                PayslipLine(
                    payslip_id=payslip.id, kind="deduction", label=line.label, amount=line.amount
                )
            )
        self.db.add(
            PayslipLine(payslip_id=payslip.id, kind="earning", label="Basic", amount=data.basic)
        )
        if data.other_allowances:
            self.db.add(
                PayslipLine(
                    payslip_id=payslip.id,
                    kind="earning",
                    label="Other Allowances",
                    amount=data.other_allowances,
                )
            )
        self.db.add(
            AuditLog(
                actor="system",
                action="create",
                entity="payslip",
                entity_id=payslip.id,
            )
        )
        self.db.commit()
        return self._to_dict(payslip)

    def get_payslip(self, payslip_id: str) -> dict[str, Any] | None:
        payslip = self.db.get(Payslip, payslip_id)
        return self._to_dict(payslip) if payslip else None

    def get_or_404(self, payslip_id: str) -> dict[str, Any]:
        result = self.get_payslip(payslip_id)
        if not result:
            raise AppError(404, "not_found", "Payslip not found")
        return result

    def list_payslips(
        self,
        month: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        stmt = select(Payslip)
        if month:
            stmt = stmt.where(Payslip.month == month)
        if status:
            stmt = stmt.where(Payslip.status == status)
        rows = list(
            self.db.scalars(
                stmt.order_by(Payslip.created_at.desc()).offset(skip).limit(limit)
            ).all()
        )
        return [self._to_dict(p) for p in rows]

    def update_status(self, payslip_id: str, new_status: str) -> dict[str, Any] | None:
        """Lifecycle: draft -> generated -> sent (F-PAY-13)."""
        payslip = self.db.get(Payslip, payslip_id)
        if not payslip:
            return None
        flow = {("draft", "generated"), ("generated", "sent")}
        if (payslip.status, new_status) not in flow:
            return None
        payslip.status = new_status
        payslip.updated_at = datetime.now(UTC)
        self.db.add(
            AuditLog(
                actor="system",
                action="status_change",
                entity="payslip",
                entity_id=payslip.id,
            )
        )
        self.db.commit()
        return self._to_dict(payslip)

    def _line_dicts(self, payslip_id: str) -> list[dict[str, Any]]:
        lines = list(
            self.db.scalars(
                select(PayslipLine).where(PayslipLine.payslip_id == payslip_id)
            ).all()
        )
        return [
            {"kind": line.kind, "label": line.label, "amount": float(line.amount)}
            for line in lines
        ]

    def _to_dict(self, payslip: Payslip) -> dict[str, Any]:
        return {
            "id": payslip.id,
            "employee_code": payslip.employee_code,
            "month": payslip.month,
            "revision": payslip.revision,
            "status": payslip.status,
            "gross": float(payslip.gross) if payslip.gross else 0.0,
            "total_deductions": float(payslip.total_deductions)
            if payslip.total_deductions
            else 0.0,
            "net": float(payslip.net) if payslip.net else 0.0,
            "net_in_words": payslip.net_in_words or "",
            "issued_on": payslip.issued_on.isoformat() if payslip.issued_on else None,
            "lines": self._line_dicts(payslip.id),
        }
