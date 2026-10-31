"""Policy engine: deterministic rules for security and escalation (never delegated to the LLM)."""
from typing import Optional

from .schemas import DATA_INTENTS, IntentName, NLUResult

SENSITIVE_COMPLAINTS = {"unauthorised_txn"}

# What the agent may do per intent. Anything not listed has no tool access.
TOOL_ALLOW_LIST = {
    IntentName.loan_status: ["LOS.applications"],
    IntentName.emi_enquiry: ["LMS.loans", "LOS.applications"],
    IntentName.repayment_schedule: ["LMS.loans", "LOS.applications", "CSM.create_ticket"],
    IntentName.loan_statement: ["LMS.loans", "LOS.applications", "CSM.create_ticket"],
    IntentName.account_balance: ["CBS.accounts"],
    IntentName.transaction_status: ["CBS.transactions"],
    IntentName.ticket_status: ["CSM.get_ticket", "CSM.tickets"],
    IntentName.policy_enquiry: ["INS.policies"],
    IntentName.claim_status: ["INS.claims"],
    IntentName.complaint: ["CSM.create_ticket"],
    IntentName.unauthorised_action: ["CSM.create_ticket"],
    IntentName.unknown: ["CSM.create_ticket"],
    IntentName.faq: ["KB.search"],
}


def needs_verification(intent: IntentName) -> bool:
    return intent in DATA_INTENTS


def escalation_trigger(nlu: NLUResult) -> Optional[tuple[str, str]]:
    """Return (reason, priority) when this turn must go to a human."""
    names = {i.name for i in nlu.intents}
    if IntentName.complaint in names and nlu.entities.complaint_category in SENSITIVE_COMPLAINTS:
        return "sensitive_intent", "HIGH"
    if IntentName.human_handoff in names:
        return "user_asks_human", "NORMAL"
    if nlu.sentiment == "angry":
        return "negative_sentiment", "NORMAL"
    return None
