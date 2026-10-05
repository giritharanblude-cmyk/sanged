from datetime import date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class PayslipCreate(BaseModel):
    employee_code: str
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    total_working_days: int = Field(ge=1, le=31)
    days_paid: int = Field(ge=0)
    basic: Decimal = Field(ge=0)
    other_allowances: Decimal = Decimal(0)
    deduction_lines: list[dict] = []
    payment_mode: str = ""
    date_of_issue: Optional[date] = None
    employee_name: str = ""
    designation: str = ""
    date_of_joining: Optional[date] = None
    aadhaar: str = ""


class PayslipLineOut(BaseModel):
    kind: str
    label: str
    amount: Decimal


class PayslipOut(BaseModel):
    id: str
    employee_code: Optional[str]
    month: str
    revision: int
    status: str
    gross: Decimal
    total_deductions: Decimal
    net: Decimal
    net_in_words: str
    issued_on: Optional[date]
    lines: list[PayslipLineOut] = []