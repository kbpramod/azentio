from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import AliasChoices, BaseModel, Field


# ---------------- Session Schemas ----------------

class SessionCreate(BaseModel):
    customer_id: Optional[str] = Field(None, description="Optional customer ID to associate initially")
    channel: str = Field("voice", description="Interaction channel (voice, web_voice, chat)")


class SessionOut(BaseModel):
    session_id: str
    call_id: str
    customer_id: Optional[str] = None
    current_state: str
    verified: bool
    failed_verification_attempts: int
    locked: bool
    created_at: datetime
    greeting: Optional[str] = None

    model_config = {"from_attributes": True}


class VerifyRequest(BaseModel):
    customer_id: str = Field(..., min_length=1, description="Customer Identifier e.g. C1023")
    dob: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Date of birth in YYYY-MM-DD format")


class VerifyResponse(BaseModel):
    session_id: str
    verified: bool
    customer_id: str
    customer_name: str
    current_state: str
    message: str


class TurnRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Speech transcript or user text")
    input_type: str = Field("voice_transcript", description="Type of input: voice_transcript, text")


class TurnResponse(BaseModel):
    turn_id: str
    session_id: str
    call_id: str
    turn_number: int
    reply_text: str
    detected_intents: List[str] = []
    state: str
    verified: bool
    tickets: List[str] = []
    escalation: Optional[str] = None
    # extra detail from the AI service (Member 2); absent when the keyword fallback answers
    transcript: Optional[str] = None
    stt_confidence: Optional[float] = None
    reply_audio_url: Optional[str] = None
    sources: List[dict] = []
    ticket_details: List[dict] = []
    escalation_detail: Optional[dict] = None
    agent_state: Optional[str] = None
    engine: str = "rules"


class EscalateRequest(BaseModel):
    reason: str = Field(..., min_length=1, description="Reason for escalating to human agent")
    category: Optional[str] = Field("complaint", description="Escalation category")
    priority: Optional[str] = Field("HIGH", description="Priority level")


class EscalateResponse(BaseModel):
    session_id: str
    call_id: str
    escalated: bool
    escalation_id: str
    ticket_id: Optional[str] = None
    message: str


class EndSessionRequest(BaseModel):
    reason: Optional[str] = Field("Customer ended interaction", description="Reason for session closure")


class EndSessionResponse(BaseModel):
    session_id: str
    call_id: str
    status: str
    message: str


# ---------------- Banking Schemas ----------------

class LoanApplicationOut(BaseModel):
    application_id: str
    product_type: str
    requested_amount: float
    application_status: str
    pending_documents: List[str] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class LOSResponse(BaseModel):
    customer_id: str
    applications: List[LoanApplicationOut]
    source: str = "LOS-SIMULATED"


class LoanOut(BaseModel):
    loan_id: str
    customer_id: str
    application_id: Optional[str] = None
    product_type: str
    outstanding_amount: float
    emi_amount: float
    next_due_date: str
    overdue_amount: float
    loan_status: str
    source: str = "LMS-SIMULATED"

    model_config = {"from_attributes": True}


class EMIScheduleOut(BaseModel):
    schedule_id: str
    installment_number: int
    due_date: str
    amount: float
    payment_status: str

    model_config = {"from_attributes": True}


class LMSScheduleResponse(BaseModel):
    loan_id: str
    schedule: List[EMIScheduleOut]
    source: str = "LMS-SIMULATED"


class AccountOut(BaseModel):
    account_id: str
    customer_id: str
    masked_account: str
    account_type: str
    balance: float
    currency: str
    account_status: str
    source: str = "CBS-SIMULATED"

    model_config = {"from_attributes": True}


class CBSTransactionOut(BaseModel):
    transaction_id: str
    account_id: str
    amount: float
    transaction_type: str
    transaction_status: str
    transaction_date: datetime
    merchant_description: str
    source: str = "CBS-SIMULATED"

    model_config = {"from_attributes": True}


# ---------------- CSM Ticket Schemas ----------------

class TicketCreateRequest(BaseModel):
    customer_id: str = Field(..., min_length=1)
    type: str = Field("service_request", description="service_request, complaint, dispute")
    category: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    priority: str = Field("NORMAL", description="LOW, NORMAL, HIGH, URGENT")
    call_id: Optional[str] = None
    idempotency_key: str = Field(..., min_length=1, description="Unique client key for atomic deduplication")


class TicketOut(BaseModel):
    ticket_id: str
    status: str
    customer_id: Optional[str] = None  # complaints/fallbacks can be raised before verification
    type: str = Field("service_request", validation_alias=AliasChoices("type", "ticket_type"))
    category: str
    summary: str
    priority: str
    call_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


# ---------------- Operations Schemas ----------------

class CallSummaryOut(BaseModel):
    call_id: str
    session_id: str
    customer_id: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    outcome: str
    escalation_status: str

    model_config = {"from_attributes": True}


class CallListResponse(BaseModel):
    total: int
    calls: List[CallSummaryOut]


class TurnOut(BaseModel):
    turn_id: str
    turn_number: int
    transcript: str
    reply_text: str
    detected_intents: List[str] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditEventOut(BaseModel):
    event_type: str
    event_status: str
    created_at: datetime
    safe_metadata: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class CallDetailOut(BaseModel):
    call_id: str
    session_id: str
    customer_id: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    outcome: str
    escalation_status: str
    turns: List[TurnOut] = []
    tickets: List[str] = []
    audit_events: List[AuditEventOut] = []

    model_config = {"from_attributes": True}


class TicketListResponse(BaseModel):
    total: int
    tickets: List[TicketOut]


class EscalationOut(BaseModel):
    escalation_id: str
    call_id: str
    session_id: str
    customer_id: Optional[str] = None
    reason: str
    ticket_id: Optional[str] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class EscalationListResponse(BaseModel):
    total: int
    escalations: List[EscalationOut]
