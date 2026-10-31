"""Shared data shapes. These match the API contract in the team handbook (section 4)."""
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class IntentName(str, Enum):
    loan_status = "loan_status"
    emi_enquiry = "emi_enquiry"
    repayment_schedule = "repayment_schedule"
    loan_statement = "loan_statement"
    account_balance = "account_balance"
    transaction_status = "transaction_status"
    ticket_status = "ticket_status"
    complaint = "complaint"
    policy_enquiry = "policy_enquiry"
    claim_status = "claim_status"
    faq = "faq"
    human_handoff = "human_handoff"
    third_party_request = "third_party_request"
    unauthorised_action = "unauthorised_action"
    provide_info = "provide_info"
    goodbye = "goodbye"
    unknown = "unknown"


# Intents that read a customer's private records -> need verification first
DATA_INTENTS = {
    IntentName.loan_status, IntentName.emi_enquiry, IntentName.repayment_schedule,
    IntentName.loan_statement, IntentName.account_balance, IntentName.transaction_status,
    IntentName.ticket_status, IntentName.policy_enquiry, IntentName.claim_status,
}

Product = Literal["personal", "vehicle", "home"]
ComplaintCategory = Literal["failed_txn", "unauthorised_txn", "incorrect_charge", "service_quality", "other"]


class Entities(BaseModel):
    customer_id: Optional[str] = None
    dob: Optional[str] = None  # YYYY-MM-DD
    product: Optional[Product] = None
    ticket_id: Optional[str] = None
    txn_id: Optional[str] = None
    complaint_category: Optional[ComplaintCategory] = None


class Intent(BaseModel):
    name: IntentName
    confidence: float = 1.0


class NLUResult(BaseModel):
    intents: list[Intent]
    entities: Entities = Field(default_factory=Entities)
    sentiment: Literal["positive", "neutral", "negative", "angry"] = "neutral"
    is_correction: bool = False
    source: Literal["llm", "rules"] = "rules"


class Source(BaseModel):
    system: str
    ref: str


class TicketRef(BaseModel):
    ticket_id: str
    type: str
    category: Optional[str] = None
    status: str = "OPEN"


class Escalation(BaseModel):
    reason: str
    priority: Literal["LOW", "NORMAL", "HIGH"] = "NORMAL"
    summary: str = ""
    intents: list[str] = []
    steps_tried: list[str] = []
    ticket_id: Optional[str] = None


class TurnRequest(BaseModel):
    text: str


class TurnResponse(BaseModel):
    session_id: str
    transcript: str
    stt_confidence: Optional[float] = None
    intents: list[Intent] = []
    state: str
    verified: bool
    reply_text: str
    reply_audio_url: Optional[str] = None
    sources: list[Source] = []
    tickets: list[TicketRef] = []
    escalation: Optional[Escalation] = None
    latency_ms: dict[str, int] = {}
