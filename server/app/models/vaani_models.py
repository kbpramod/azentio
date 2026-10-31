from datetime import date, datetime, timezone
from typing import Any, List, Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.types import Date, JSON, TypeDecorator
from app.db.session import Base


def utcnow():
    return datetime.now(timezone.utc)


class StringDate(TypeDecorator):
    """Store as native DATE in Postgres/SQLite, interact in Python as YYYY-MM-DD string."""
    impl = Date
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return date.fromisoformat(value.strip())
            except Exception:
                return None
        if isinstance(value, datetime):
            return value.date()
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, (date, datetime)):
            return value.strftime("%Y-%m-%d")
        return str(value)


class ArrayOrJSON(TypeDecorator):
    """Use PostgreSQL ARRAY(Text) when on postgres, JSON when on sqlite."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(ARRAY(Text))
        return dialect.type_descriptor(JSON)

    def process_bind_param(self, value, dialect):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [str(value)]

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return list(value)


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String(50), primary_key=True, index=True)
    customer_name = Column("name", String(255), nullable=False)
    dob = Column("dob", StringDate, nullable=False, index=True)  # YYYY-MM-DD
    phone_number = Column("phone_masked", String(50), nullable=True)
    email = Column("email_masked", String(255), nullable=True)
    preferred_lang = Column("preferred_lang", String(20), default="en", nullable=True)
    user_id = Column("user_id", Integer, nullable=True)

    @property
    def name(self) -> str:
        return self.customer_name

    @name.setter
    def name(self, val: str) -> None:
        self.customer_name = val

    loan_applications = relationship("LoanApplication", back_populates="customer", cascade="all, delete-orphan")
    loans = relationship("Loan", back_populates="customer", cascade="all, delete-orphan")
    accounts = relationship("Account", back_populates="customer", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="customer", cascade="all, delete-orphan")


class LoanApplication(Base):
    __tablename__ = "loan_applications"

    application_id = Column("app_id", String(50), primary_key=True, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id", ondelete="SET NULL"), nullable=True, index=True)
    product_type = Column("product", String(100), nullable=False)
    requested_amount = Column("amount", Float, nullable=False)
    applied_on = Column("applied_on", StringDate, default=date.today, nullable=False)
    application_status = Column("stage", String(50), default="DOC_VERIFICATION", nullable=False)
    pending_documents = Column("pending_items", ArrayOrJSON, default=list, nullable=False)

    @property
    def created_at(self) -> datetime:
        if isinstance(self.applied_on, (date, datetime)):
            return datetime.combine(self.applied_on, datetime.min.time(), tzinfo=timezone.utc)
        return utcnow()

    @property
    def app_id(self) -> str:
        return self.application_id

    @property
    def product(self) -> str:
        return self.product_type

    @property
    def stage(self) -> str:
        return self.application_status

    customer = relationship("Customer", back_populates="loan_applications")


class Loan(Base):
    __tablename__ = "loans"

    loan_id = Column(String(50), primary_key=True, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id", ondelete="SET NULL"), nullable=True, index=True)
    product_type = Column("product", String(100), nullable=False)
    principal = Column("principal", Float, default=0.0, nullable=True)
    outstanding_amount = Column("outstanding", Float, nullable=False)
    emi_amount = Column("emi_amount", Float, nullable=False)
    next_due_date = Column("next_due_date", StringDate, nullable=True)
    overdue_amount = Column("overdue_amount", Float, default=0.0, nullable=False)
    loan_status = Column("status", String(50), default="ACTIVE", nullable=False)

    @property
    def application_id(self) -> Optional[str]:
        return None

    @property
    def product(self) -> str:
        return self.product_type

    @property
    def outstanding(self) -> float:
        return self.outstanding_amount

    @property
    def status(self) -> str:
        return self.loan_status

    customer = relationship("Customer", back_populates="loans")
    schedules = relationship("EMISchedule", back_populates="loan", cascade="all, delete-orphan")


class EMISchedule(Base):
    __tablename__ = "emi_schedule"

    loan_id = Column(String(50), ForeignKey("loans.loan_id"), primary_key=True, index=True)
    installment_number = Column("n", Integer, primary_key=True)
    due_date = Column("due_date", StringDate, nullable=False)
    amount = Column("amount", Float, nullable=False)
    payment_status = Column("status", String(50), default="PENDING", nullable=False)

    @property
    def schedule_id(self) -> str:
        return f"SCH-{self.loan_id}-{self.installment_number}"

    loan = relationship("Loan", back_populates="schedules")


class Account(Base):
    __tablename__ = "accounts"

    account_id = Column(String(50), primary_key=True, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id", ondelete="SET NULL"), nullable=True, index=True)
    account_type = Column("type", String(50), default="savings", nullable=False)
    balance = Column("balance", Float, default=0.0, nullable=False)
    currency = Column("currency", String(10), default="INR", nullable=False)

    @property
    def account_number(self) -> str:
        return self.account_id

    @property
    def account_status(self) -> str:
        return "ACTIVE"

    customer = relationship("Customer", back_populates="accounts")


class CBSTransaction(Base):
    __tablename__ = "cbs_transactions"

    transaction_id = Column(String(50), primary_key=True, index=True)
    account_id = Column(String(50), ForeignKey("accounts.account_id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String(50), nullable=False)  # DEBIT, CREDIT
    transaction_status = Column(String(50), default="SUCCESS", nullable=False)
    transaction_date = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    merchant_description = Column(String(255), nullable=False)


class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(String(50), primary_key=True, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=True, index=True)
    channel = Column(String(50), default="voice", nullable=False)
    current_state = Column(String(50), default="UNVERIFIED", nullable=False)
    verified = Column(Boolean, default=False, nullable=False)
    failed_verification_attempts = Column(Integer, default=0, nullable=False)
    locked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    calls = relationship(
        "Call",
        back_populates="session",
        cascade="all, delete-orphan",
        primaryjoin="Session.session_id == Call.session_id",
        foreign_keys="[Call.session_id]",
    )


class Call(Base):
    __tablename__ = "calls"

    call_id = Column(String(50), primary_key=True, index=True)
    session_id = Column(String(50), ForeignKey("sessions.session_id"), nullable=True, index=True)
    customer_id = Column(String(50), nullable=True, index=True)
    started_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    outcome = Column(String(50), default="IN_PROGRESS", nullable=False)
    escalation_status = Column(String(50), default="NONE", nullable=False)

    session = relationship(
        "Session",
        back_populates="calls",
        primaryjoin="Call.session_id == Session.session_id",
        foreign_keys="[Call.session_id]",
    )
    turns = relationship("ConversationTurn", back_populates="call", cascade="all, delete-orphan")


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"

    turn_id = Column(String(50), primary_key=True, index=True)
    call_id = Column(String(50), ForeignKey("calls.call_id"), nullable=False, index=True)
    session_id = Column(String(50), nullable=False, index=True)
    turn_number = Column(Integer, nullable=False)
    input_type = Column(String(50), default="voice_transcript", nullable=False)
    transcript = Column(Text, nullable=False)
    detected_intents = Column(JSON, default=list, nullable=False)
    reply_text = Column(Text, nullable=False)
    processing_status = Column(String(50), default="COMPLETED", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    call = relationship("Call", back_populates="turns")


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id = Column(String(50), primary_key=True, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id", ondelete="SET NULL"), nullable=True, index=True)
    session_id = Column(String(50), nullable=True, index=True)
    call_id = Column(String(50), nullable=True, index=True)
    ticket_type = Column("type", String(50), default="service_request", nullable=False)
    category = Column("category", String(100), nullable=True)
    summary = Column("summary", Text, nullable=True)
    priority = Column("priority", String(20), default="NORMAL", nullable=True)
    status = Column("status", String(50), default="OPEN", nullable=True)
    escalated = Column("escalated", Boolean, default=False, nullable=True)
    escalation_reason = Column("escalation_reason", Text, nullable=True)
    idempotency_key = Column("idempotency_key", String(100), unique=True, index=True, nullable=True)
    created_at = Column("created_at", DateTime(timezone=True), default=utcnow, nullable=False)

    @property
    def type(self) -> str:
        return self.ticket_type

    @type.setter
    def type(self, value: str) -> None:
        self.ticket_type = value

    customer = relationship("Customer", back_populates="tickets")


class Escalation(Base):
    __tablename__ = "escalations"

    escalation_id = Column(String(50), primary_key=True, index=True)
    call_id = Column(String(50), nullable=False, index=True)
    session_id = Column(String(50), nullable=False, index=True)
    customer_id = Column(String(50), nullable=True, index=True)
    reason = Column(Text, nullable=False)
    ticket_id = Column(String(50), nullable=True)
    status = Column(String(50), default="PENDING_AGENT", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    audit_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), nullable=True, index=True)
    call_id = Column(String(50), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    event_status = Column(String(50), default="SUCCESS", nullable=False)
    safe_metadata = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)


class EscalationTicket(Base):
    __tablename__ = "escalation_tickets"

    escalation_ticket_id = Column(String(50), primary_key=True, index=True)
    ticket_id = Column(String(50), nullable=True, index=True)
    session_id = Column(String(50), nullable=False, index=True)
    call_id = Column(String(50), nullable=True, index=True)
    customer_id = Column(String(50), nullable=True, index=True)
    customer_name = Column(String(100), nullable=True)
    customer_email = Column(String(100), nullable=True)
    reason = Column(Text, nullable=False)
    query_summary = Column(Text, nullable=True)
    transcript = Column(Text, nullable=True)
    ai_turns_count = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="PENDING_HUMAN_REVIEW", nullable=False)
    priority = Column(String(20), default="HIGH", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
