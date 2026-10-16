"""SQLAlchemy 2.0 typed models — single metadata for app and Alembic.

Mapped[]/mapped_column() is used deliberately (not the legacy Column() style):
mypy strict then sees real instance types (str, Decimal, ...) instead of the
Column[] descriptors, which removes an entire class of arg-type errors without
a single type: ignore.
"""
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Single declarative base shared by models and Alembic (docs section 3.2)."""


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="master")
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class OtpChallenge(Base):
    __tablename__ = "otp_challenges"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False
    )
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    last_activity: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[str | None] = mapped_column(String(100))
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class NumberSequence(Base):
    __tablename__ = "number_sequences"

    series: Mapped[str] = mapped_column(String(20), primary_key=True)
    fy: Mapped[str] = mapped_column(String(6), primary_key=True)
    last_value: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class File(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    mime: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    employee_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    dob: Mapped[Any | None] = mapped_column(Date)
    address: Mapped[str | None] = mapped_column(Text)
    salary: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    contact_no: Mapped[str | None] = mapped_column(String(20))
    office_no: Mapped[str | None] = mapped_column(String(20))
    designation: Mapped[str | None] = mapped_column(String(200))
    office_address: Mapped[str | None] = mapped_column(Text)
    aadhaar_enc: Mapped[str | None] = mapped_column(Text)
    aadhaar_last4: Mapped[str | None] = mapped_column(String(4))
    email: Mapped[str | None] = mapped_column(String(255))
    blood_group: Mapped[str | None] = mapped_column(String(10))
    date_of_joining: Mapped[Any | None] = mapped_column(Date)
    payment_mode: Mapped[str | None] = mapped_column(String(50))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class EmployeeDocument(Base):
    __tablename__ = "employee_documents"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    employee_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("employees.id"), nullable=False
    )
    file_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    description: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class CompanyProfile(Base):
    __tablename__ = "company_profile"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    gstin: Mapped[str | None] = mapped_column(String(15))
    incorporation_no: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    website: Mapped[str | None] = mapped_column(String(255))
    signatory: Mapped[str | None] = mapped_column(String(200))
    pf_applicable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class Payslip(Base):
    __tablename__ = "payslips"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    employee_code: Mapped[str | None] = mapped_column(String(50))
    month: Mapped[str] = mapped_column(String(7), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    total_working_days: Mapped[int | None] = mapped_column(Integer)
    days_paid: Mapped[int | None] = mapped_column(Integer)
    gross: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    total_deductions: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    net: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    net_in_words: Mapped[str | None] = mapped_column(String(500))
    issued_on: Mapped[Any | None] = mapped_column(Date)
    employee_ref: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class PayslipLine(Base):
    __tablename__ = "payslip_lines"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    payslip_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("payslips.id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class PayslipDelivery(Base):
    __tablename__ = "payslip_deliveries"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    payslip_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("payslips.id"), nullable=False
    )
    to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class Bill(Base):
    __tablename__ = "bills"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    serial: Mapped[str | None] = mapped_column(String(20), unique=True)
    vendor: Mapped[str | None] = mapped_column(String(200))
    bill_date: Mapped[Any | None] = mapped_column(Date)
    total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    category: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    payment_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    review_state: Mapped[str] = mapped_column(
        String(20), nullable=False, default="needs_review"
    )
    file_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="upload")
    source_ref: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    extraction_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class BillItem(Base):
    __tablename__ = "bill_items"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    bill_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("bills.id"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(String(500))
    qty: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class Voucher(Base):
    __tablename__ = "vouchers"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    serial: Mapped[str | None] = mapped_column(String(20), unique=True)
    voucher_date: Mapped[Any | None] = mapped_column(Date)
    payee: Mapped[str | None] = mapped_column(String(200))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    category: Mapped[str | None] = mapped_column(String(100))
    file_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class StockItem(Base):
    __tablename__ = "stock_items"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    unit: Mapped[str | None] = mapped_column(String(50))
    reorder_level: Mapped[int | None] = mapped_column(Integer)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    item_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("stock_items.id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(10), nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class ChannelSender(Base):
    __tablename__ = "channel_senders"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    phone_enc: Mapped[str | None] = mapped_column(Text)
    phone_hash: Mapped[str | None] = mapped_column(String(64))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class InboundMessage(Base):
    __tablename__ = "inbound_messages"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    kind: Mapped[str | None] = mapped_column(String(20))
    mime: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="received")
    reject_reason: Mapped[str | None] = mapped_column(String(255))
    file_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    bill_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False))
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
