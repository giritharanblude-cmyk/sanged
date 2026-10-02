import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeMeta, declarative_base

Base: DeclarativeMeta = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="master")
    email = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class OtpChallenge(Base):
    __tablename__ = "otp_challenges"
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    purpose = Column(String(50), nullable=False)
    code_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class Session(Base):
    __tablename__ = "sessions"
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(255), unique=True, nullable=False)
    ip_address = Column(String(45), nullable=True)
    last_activity = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor = Column(String(100), nullable=False)
    action = Column(String(50), nullable=False)
    entity = Column(String(50), nullable=True)
    entity_id = Column(String(100), nullable=True)
    meta = Column(JSONB, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class NumberSequence(Base):
    __tablename__ = "number_sequences"
    series = Column(String(20), primary_key=True)
    fy = Column(String(6), primary_key=True)
    last_value = Column(BigInteger, nullable=False, default=0)


class File(Base):
    __tablename__ = "files"
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    sha256 = Column(String(64), nullable=False, unique=True)
    mime = Column(String(100), nullable=False)
    size = Column(BigInteger, nullable=False)
    storage_key = Column(String(255), nullable=False)
    uploaded_by = Column(UUID(as_uuid=False), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class Employee(Base):
    __tablename__ = "employees"
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_code = Column(String(50), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    dob = Column(Date, nullable=True)
    address = Column(Text, nullable=True)
    salary = Column(Numeric(14, 2), nullable=True)
    contact_no = Column(String(20), nullable=True)
    office_no = Column(String(20), nullable=True)
    designation = Column(String(200), nullable=True)
    office_address = Column(Text, nullable=True)
    aadhaar_enc = Column(Text, nullable=True)
    aadhaar_last4 = Column(String(4), nullable=True)
    email = Column(String(255), nullable=True)
    blood_group = Column(String(10), nullable=True)
    date_of_joining = Column(Date, nullable=True)
    payment_mode = Column(String(50), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class EmployeeDocument(Base):
    __tablename__ = "employee_documents"
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(UUID(as_uuid=False), ForeignKey("employees.id"), nullable=False)
    file_id = Column(UUID(as_uuid=False), nullable=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class CompanyProfile(Base):
    __tablename__ = "company_profile"
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    legal_name = Column(String(255), nullable=False)
    gstin = Column(String(15), nullable=True)
    incorporation_no = Column(String(100), nullable=True)
    address = Column(Text, nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    website = Column(String(255), nullable=True)
    signatory = Column(String(200), nullable=True)
    pf_applicable = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class Payslip(Base):
    __tablename__ = "payslips"
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_code = Column(String(50), nullable=True)
    month = Column(String(7), nullable=False)
    revision = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="draft")
    snapshot = Column(JSONB, nullable=True)
    total_working_days = Column(Integer, nullable=True)
    days_paid = Column(Integer, nullable=True)
    gross = Column(Numeric(14, 2), nullable=True)
    total_deductions = Column(Numeric(14, 2), nullable=True)
    net = Column(Numeric(14, 2), nullable=True)
    net_in_words = Column(String(500), nullable=True)
    issued_on = Column(Date, nullable=True)
    employee_ref = Column(UUID(as_uuid=False), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class PayslipLine(Base):
    __tablename__ = "payslip_lines"
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    payslip_id = Column(UUID(as_uuid=False), ForeignKey("payslips.id"), nullable=False)
    kind = Column(String(20), nullable=False)
    label = Column(String(200), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class PayslipDelivery(Base):
    __tablename__ = "payslip_deliveries"
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    payslip_id = Column(UUID(as_uuid=False), ForeignKey("payslips.id"), nullable=False)
    to_email = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class Bill(Base):
    __tablename__ = "bills"
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    serial = Column(String(20), unique=True, nullable=True)
    vendor = Column(String(200), nullable=True)
    bill_date = Column(Date, nullable=True)
    total = Column(Numeric(14, 2), nullable=True)
    category = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, default="draft")
    payment_status = Column(String(20), nullable=False, default="pending")
    review_state = Column(String(20), nullable=False, default="needs_review")
    file_id = Column(UUID(as_uuid=False), nullable=True)
    source = Column(String(20), nullable=False, default="upload")
    source_ref = Column(UUID(as_uuid=False), nullable=True)
    extraction_confidence = Column(Numeric(5, 2), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class BillItem(Base):
    __tablename__ = "bill_items"
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    bill_id = Column(UUID(as_uuid=False), ForeignKey("bills.id"), nullable=False)
    description = Column(String(500), nullable=True)
    qty = Column(Numeric(14, 2), nullable=True)
    unit_price = Column(Numeric(14, 2), nullable=True)
    amount = Column(Numeric(14, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class Voucher(Base):
    __tablename__ = "vouchers"
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    serial = Column(String(20), unique=True, nullable=True)
    voucher_date = Column(Date, nullable=True)
    payee = Column(String(200), nullable=True)
    amount = Column(Numeric(14, 2), nullable=True)
    category = Column(String(100), nullable=True)
    file_id = Column(UUID(as_uuid=False), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class StockItem(Base):
    __tablename__ = "stock_items"
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    sku = Column(String(100), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=True)
    unit = Column(String(50), nullable=True)
    reorder_level = Column(Integer, nullable=True)
    unit_cost = Column(Numeric(14, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    item_id = Column(UUID(as_uuid=False), ForeignKey("stock_items.id"), nullable=False)
    kind = Column(String(10), nullable=False)
    qty = Column(Integer, nullable=False)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class ChannelSender(Base):
    __tablename__ = "channel_senders"
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(UUID(as_uuid=False), nullable=True)
    channel = Column(String(20), nullable=False)
    phone_enc = Column(Text, nullable=True)
    phone_hash = Column(String(64), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class InboundMessage(Base):
    __tablename__ = "inbound_messages"
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider = Column(String(20), nullable=False)
    provider_message_id = Column(String(255), nullable=False)
    sender_id = Column(UUID(as_uuid=False), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=False)
    kind = Column(String(20), nullable=True)
    mime = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, default="received")
    reject_reason = Column(String(255), nullable=True)
    file_id = Column(UUID(as_uuid=False), nullable=True)
    bill_id = Column(UUID(as_uuid=False), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
