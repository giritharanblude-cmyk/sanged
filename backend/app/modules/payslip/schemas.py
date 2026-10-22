"""Payslip API schemas: pydantic validation surfaces (F-PAY-02, F-PAY-09)."""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.money import Money


class DeductionLineIn(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    amount: Decimal = Field(ge=0)


class PayslipCreate(BaseModel):
    employee_code: str = Field(min_length=1, max_length=50)
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    total_working_days: int = Field(ge=1, le=31)
    days_paid: int = Field(ge=0, le=31)
    basic: Decimal = Field(ge=0)
    other_allowances: Decimal = Decimal("0")
    deduction_lines: list[DeductionLineIn] = []
    payment_mode: str = ""
    date_of_issue: date | None = None
    employee_name: str = ""
    designation: str = ""
    date_of_joining: date | None = None
    aadhaar: str = ""


class PayslipLineOut(BaseModel):
    kind: str
    label: str
    amount: Money


class PayslipOut(BaseModel):
    id: str
    employee_code: str | None
    month: str
    revision: int
    status: str
    gross: Money
    total_deductions: Money
    net: Money
    net_in_words: str
    issued_on: date | None
    lines: list[PayslipLineOut] = []
