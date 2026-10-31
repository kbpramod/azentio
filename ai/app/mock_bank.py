"""SIMULATED banking systems (LOS, LMS, CBS, Insurance, CSM) with synthetic data.

Temporary stand-in until Member B's API is ready. Shapes follow the team API contract.
All customers and values are fictional.
"""
import copy
import itertools

CUSTOMERS = {
    "C1023": {"customer_id": "C1023", "name": "R. Sharma", "dob": "1995-03-12"},
    "C1045": {"customer_id": "C1045", "name": "A. Khan", "dob": "1988-07-21"},
    "C1188": {"customer_id": "C1188", "name": "S. Iyer", "dob": "1979-11-02"},
    "C1077": {"customer_id": "C1077", "name": "M. Fernandes", "dob": "1990-01-30"},
}

APPLICATIONS = [
    {"app_id": "APP-77", "customer_id": "C1023", "product": "personal", "amount": 300000,
     "applied_on": "2026-10-24", "stage": "DOC_VERIFICATION", "pending_items": ["salary slip"]},
]

LOANS = [
    {"loan_id": "LN-501", "customer_id": "C1045", "product": "vehicle", "principal": 600000,
     "outstanding": 412300, "emi_amount": 8450, "next_due_date": "2026-11-05", "overdue_amount": 0, "status": "ACTIVE"},
    {"loan_id": "LN-502", "customer_id": "C1045", "product": "personal", "principal": 200000,
     "outstanding": 96500, "emi_amount": 6120, "next_due_date": "2026-11-10", "overdue_amount": 0, "status": "ACTIVE"},
    {"loan_id": "LN-610", "customer_id": "C1077", "product": "home", "principal": 3500000,
     "outstanding": 2875000, "emi_amount": 31200, "next_due_date": "2026-11-07", "overdue_amount": 31200, "status": "ACTIVE"},
]

ACCOUNTS = [
    {"account_id": "AC-4521", "customer_id": "C1188", "type": "savings", "balance": 58210, "currency": "INR"},
    {"account_id": "AC-7781", "customer_id": "C1045", "type": "savings", "balance": 124500, "currency": "INR"},
]

TRANSACTIONS = [
    {"txn_id": "TX-9001", "account_id": "AC-4521", "date": "2026-10-28", "amount": 20000,
     "direction": "debit", "status": "SUCCESS", "merchant": "Online transfer"},
    {"txn_id": "TX-9002", "account_id": "AC-7781", "date": "2026-10-30", "amount": 4500,
     "direction": "debit", "status": "PENDING", "merchant": "UPI payment"},
]

POLICIES = [
    {"policy_id": "POL-300", "customer_id": "C1077", "type": "health", "status": "ACTIVE",
     "premium": 14500, "premium_due": "2026-12-01", "sum_assured": 500000},
]

CLAIMS = [
    {"claim_id": "CLM-88", "policy_id": "POL-300", "filed_on": "2026-10-15", "status": "UNDER_REVIEW"},
]

_SEED_TICKETS = [
    {"ticket_id": "SR-4400", "customer_id": "C1045", "type": "service_request", "category": "loan_statement",
     "priority": "NORMAL", "status": "IN_PROGRESS", "summary": "Loan statement for LN-502", "escalated": False},
]


class MockBank:
    """In-memory simulated systems. Every payload carries source=*-SIMULATED."""

    def __init__(self):
        self.tickets = copy.deepcopy(_SEED_TICKETS)
        self._seq = {"SR": itertools.count(4471), "CMP": itertools.count(2210)}

    # --- auth
    def verify(self, customer_id: str, dob: str) -> bool:
        c = CUSTOMERS.get(customer_id)
        return bool(c and c["dob"] == dob)

    def customer(self, customer_id: str) -> dict | None:
        return CUSTOMERS.get(customer_id)

    # --- LOS / LMS
    def applications(self, customer_id):
        return [dict(a, source="LOS-SIMULATED") for a in APPLICATIONS if a["customer_id"] == customer_id]

    def loans(self, customer_id):
        return [dict(l, source="LMS-SIMULATED") for l in LOANS if l["customer_id"] == customer_id]

    # --- CBS
    def accounts(self, customer_id):
        return [dict(a, source="CBS-SIMULATED") for a in ACCOUNTS if a["customer_id"] == customer_id]

    def transactions(self, customer_id):
        ids = {a["account_id"] for a in ACCOUNTS if a["customer_id"] == customer_id}
        return [dict(t, source="CBS-SIMULATED") for t in TRANSACTIONS if t["account_id"] in ids]

    # --- Insurance
    def policies(self, customer_id):
        return [dict(p, source="INS-SIMULATED") for p in POLICIES if p["customer_id"] == customer_id]

    def claims(self, customer_id):
        ids = {p["policy_id"] for p in POLICIES if p["customer_id"] == customer_id}
        return [dict(c, source="INS-SIMULATED") for c in CLAIMS if c["policy_id"] in ids]

    # --- CSM tickets
    def create_ticket(self, payload: dict) -> dict:
        key = payload.get("idempotency_key")
        if key:
            for t in self.tickets:
                if t.get("idempotency_key") == key:
                    return dict(t, source="CSM-SIMULATED")
        prefix = "CMP" if payload["type"] == "complaint" else "SR"
        t = {"ticket_id": f"{prefix}-{next(self._seq[prefix])}", "status": "OPEN", **payload}
        self.tickets.append(t)
        return dict(t, source="CSM-SIMULATED")

    def get_ticket(self, ticket_id):
        for t in self.tickets:
            if t["ticket_id"] == ticket_id:
                return dict(t, source="CSM-SIMULATED")
        return None

    def tickets_for(self, customer_id):
        return [dict(t, source="CSM-SIMULATED") for t in self.tickets if t.get("customer_id") == customer_id]
