"""Tool layer: the ONLY way the agent touches banking data.

- Allow-listed methods only (no generic "call any URL").
- Every read checks the session is verified (NFR N1) — enforced here, not by the LLM.
- Backend is the built-in MockBank, or Member B's HTTP API when BANKING_API_URL is set.
"""
import httpx

from . import config
from .mock_bank import MockBank


class NotVerified(Exception):
    pass


class HttpBank:
    """Client for Member B's API. Paths follow the team API contract (handbook §4)."""

    def __init__(self, base_url: str):
        self.c = httpx.Client(base_url=base_url, timeout=5.0)

    def _get(self, path, **params):
        r = self.c.get(path, params=params or None)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def verify(self, customer_id, dob):
        r = self.c.post("/mock/auth/verify", json={"customer_id": customer_id, "dob": dob})
        return r.status_code == 200 and r.json().get("verified", False)

    def customer(self, customer_id):
        return self._get(f"/mock/customers/{customer_id}")

    def applications(self, customer_id):
        return self._get("/mock/los/applications", customer_id=customer_id) or []

    def loans(self, customer_id):
        return self._get("/mock/lms/loans", customer_id=customer_id) or []

    def accounts(self, customer_id):
        return self._get("/mock/cbs/accounts", customer_id=customer_id) or []

    def transactions(self, customer_id):
        return self._get("/mock/cbs/transactions", customer_id=customer_id) or []

    def policies(self, customer_id):
        return self._get("/mock/ins/policies", customer_id=customer_id) or []

    def claims(self, customer_id):
        return self._get("/mock/ins/claims", customer_id=customer_id) or []

    def create_ticket(self, payload):
        r = self.c.post("/mock/csm/tickets", json=payload)
        r.raise_for_status()
        return r.json()

    def get_ticket(self, ticket_id):
        return self._get(f"/mock/csm/tickets/{ticket_id}")

    def tickets_for(self, customer_id):
        return self._get("/mock/csm/tickets", customer_id=customer_id) or []


def make_backend():
    return HttpBank(config.BANKING_API_URL) if config.BANKING_API_URL else MockBank()


class Tools:
    """Session-bound tools. Reads raise NotVerified unless the session is verified."""

    def __init__(self, backend, session):
        self.b = backend
        self.s = session

    def _cid(self):
        if not self.s.verified or not self.s.customer_id:
            raise NotVerified()
        return self.s.customer_id

    def _log(self, name, result):
        self.s.audit("TOOL", {"tool": name, "result_count": len(result) if isinstance(result, list) else int(result is not None)})
        return result

    # auth is the one call allowed before verification
    def verify(self, customer_id, dob):
        ok = self.b.verify(customer_id, dob)
        self.s.audit("AUTH", {"customer_id": customer_id, "ok": ok})
        return ok

    def customer(self):
        return self.b.customer(self._cid())

    def applications(self):
        return self._log("LOS.applications", self.b.applications(self._cid()))

    def loans(self):
        return self._log("LMS.loans", self.b.loans(self._cid()))

    def accounts(self):
        return self._log("CBS.accounts", self.b.accounts(self._cid()))

    def transactions(self):
        return self._log("CBS.transactions", self.b.transactions(self._cid()))

    def policies(self):
        return self._log("INS.policies", self.b.policies(self._cid()))

    def claims(self):
        return self._log("INS.claims", self.b.claims(self._cid()))

    def get_ticket(self, ticket_id):
        t = self.b.get_ticket(ticket_id)
        # never reveal someone else's ticket
        if t and t.get("customer_id") != self._cid():
            t = None
        return self._log("CSM.get_ticket", t)

    def tickets(self):
        return self._log("CSM.tickets", self.b.tickets_for(self._cid()))

    def create_ticket(self, type_, category, summary, priority="NORMAL", escalated=False, reason=None):
        """Tickets may be created before verification (complaints / fallback), so no _cid() gate."""
        payload = {
            "customer_id": self.s.customer_id if self.s.verified else None,
            "type": type_, "category": category, "summary": summary, "priority": priority,
            "escalated": escalated, "escalation_reason": reason, "call_id": self.s.id,
            "idempotency_key": f"{self.s.id}-{len(self.s.turns)}-{type_}-{category}",
        }
        t = self.b.create_ticket(payload)
        self.s.audit("TOOL", {"tool": "CSM.create_ticket", "ticket_id": t["ticket_id"]})
        return t
