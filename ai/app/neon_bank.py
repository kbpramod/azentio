"""Banking backend that reads/writes the shared Neon Postgres database (synthetic data).

Same method names and return shapes as MockBank, so the orchestrator doesn't change.
Tables are documented in server/DB_SCHEMA.md and created by the seed script.
Also records calls, turns and audit events for the ops dashboard.
"""
import json
import threading
from datetime import date, datetime

import psycopg
from psycopg.rows import dict_row

from . import config


def _clean(row: dict | None, source: str) -> dict | None:
    if row is None:
        return None
    out = {}
    for k, v in row.items():
        out[k] = v.isoformat() if isinstance(v, (date, datetime)) else v
    out["source"] = source
    return out


class NeonBank:
    def __init__(self, url: str | None = None):
        self.url = url or config.DATABASE_URL
        if not self.url:
            raise RuntimeError("DATABASE_URL is not set (ai/.env)")
        self._conn = None
        self._lock = threading.Lock()

    # one autocommit connection, reopened if Neon drops it
    def _q(self, sql: str, params=(), one=False):
        with self._lock:
            for attempt in (1, 2):
                try:
                    if self._conn is None or self._conn.closed:
                        self._conn = psycopg.connect(self.url, autocommit=True, row_factory=dict_row)
                    cur = self._conn.execute(sql, params)
                    if cur.description is None:
                        return None
                    return cur.fetchone() if one else cur.fetchall()
                except psycopg.OperationalError:
                    self._conn = None
                    if attempt == 2:
                        raise

    def _rows(self, sql, params, source):
        return [_clean(r, source) for r in self._q(sql, params)]

    # --- auth
    def verify(self, customer_id, dob):
        r = self._q("SELECT 1 FROM customers WHERE customer_id=%s AND dob=%s", (customer_id, dob), one=True)
        return r is not None

    def customer(self, customer_id):
        return _clean(self._q("SELECT customer_id, name FROM customers WHERE customer_id=%s",
                              (customer_id,), one=True), "CORE-SIMULATED")

    # --- LOS / LMS / CBS / INS
    def applications(self, customer_id):
        return self._rows("SELECT * FROM loan_applications WHERE customer_id=%s ORDER BY applied_on DESC",
                          (customer_id,), "LOS-SIMULATED")

    def loans(self, customer_id):
        return self._rows("SELECT * FROM loans WHERE customer_id=%s AND status='ACTIVE' ORDER BY loan_id",
                          (customer_id,), "LMS-SIMULATED")

    def accounts(self, customer_id):
        return self._rows("SELECT * FROM accounts WHERE customer_id=%s ORDER BY account_id",
                          (customer_id,), "CBS-SIMULATED")

    def transactions(self, customer_id):
        return self._rows("SELECT t.* FROM bank_transactions t JOIN accounts a USING (account_id) "
                          "WHERE a.customer_id=%s ORDER BY t.date", (customer_id,), "CBS-SIMULATED")

    def policies(self, customer_id):
        return self._rows("SELECT * FROM policies WHERE customer_id=%s ORDER BY policy_id",
                          (customer_id,), "INS-SIMULATED")

    def claims(self, customer_id):
        return self._rows("SELECT c.* FROM claims c JOIN policies p USING (policy_id) "
                          "WHERE p.customer_id=%s ORDER BY c.filed_on", (customer_id,), "INS-SIMULATED")

    # --- CSM tickets
    def create_ticket(self, payload: dict) -> dict:
        key = payload.get("idempotency_key")
        if key:
            existing = self._q("SELECT * FROM tickets WHERE idempotency_key=%s", (key,), one=True)
            if existing:
                return _clean(existing, "CSM-SIMULATED")
        prefix = "CMP" if payload["type"] == "complaint" else "SR"
        start = 2210 if prefix == "CMP" else 4471
        cols = ("customer_id", "type", "category", "priority", "summary", "escalated",
                "escalation_reason", "call_id", "idempotency_key")
        for _ in range(5):  # retry if two calls grab the same number
            nxt = self._q(
                # other services may use non-numeric IDs (e.g. SR-5F234A); only count numeric ones
                "SELECT GREATEST(%s, COALESCE(MAX(split_part(ticket_id,'-',2)::int)+1, %s)) AS n "
                "FROM tickets WHERE ticket_id ~ %s", (start, start, f"^{prefix}-[0-9]+$"), one=True)["n"]
            tid = f"{prefix}-{nxt}"
            try:
                row = self._q(
                    f"INSERT INTO tickets (ticket_id, {', '.join(cols)}) VALUES (%s{', %s' * len(cols)}) RETURNING *",
                    (tid, *[payload.get(c) for c in cols]), one=True)
                return _clean(row, "CSM-SIMULATED")
            except psycopg.errors.UniqueViolation:
                continue
        raise RuntimeError("could not allocate ticket id")

    def get_ticket(self, ticket_id):
        return _clean(self._q("SELECT * FROM tickets WHERE ticket_id=%s", (ticket_id,), one=True), "CSM-SIMULATED")

    def tickets_for(self, customer_id):
        return self._rows("SELECT * FROM tickets WHERE customer_id=%s ORDER BY created_at",
                          (customer_id,), "CSM-SIMULATED")

    # --- call history for the ops dashboard
    def record_turn(self, s, customer_text, reply, intents, stt_conf, latency_ms):
        outcome = {"ESCALATED": "ESCALATED", "LOCKED": "AUTH_FAIL"}.get(s.state)
        if outcome is None and any(t.type == "fallback" for t in s.tickets):
            outcome = "FALLBACK"
        if outcome is None and s.state == "CLOSED":
            outcome = "RESOLVED"
        n = len(s.turns)
        events = s.trace[getattr(s, "_audit_saved", 0):]
        # one round trip: call upsert + both turns + all new audit events
        self._q(
            "WITH c AS (INSERT INTO calls (call_id, customer_id, outcome) VALUES (%(id)s, %(cust)s, %(outcome)s) "
            "  ON CONFLICT (call_id) DO UPDATE SET customer_id=EXCLUDED.customer_id, outcome=EXCLUDED.outcome, "
            "  ended_at=CASE WHEN EXCLUDED.outcome IN ('RESOLVED','ESCALATED','AUTH_FAIL') THEN now() END "
            "  RETURNING call_id), "
            "t AS (INSERT INTO turns SELECT * FROM (VALUES "
            "  (%(id)s, %(n1)s, 'customer', %(said)s, %(intents)s::text[], %(conf)s::real, %(lat)s::int), "
            "  (%(id)s, %(n2)s, 'agent', %(reply)s, NULL::text[], NULL::real, NULL::int)) v "
            "  WHERE EXISTS (SELECT 1 FROM c) ON CONFLICT DO NOTHING) "
            "INSERT INTO audit (call_id, ts, stage, detail) "
            "SELECT %(id)s, (e->>'ts')::timestamptz, e->>'stage', e FROM jsonb_array_elements(%(events)s::jsonb) e",
            {"id": s.id, "cust": s.customer_id if s.verified else None, "outcome": outcome,
             "n1": n - 2, "said": customer_text, "intents": intents, "conf": stt_conf,
             "lat": sum(latency_ms.values()), "n2": n - 1, "reply": reply,
             "events": json.dumps(events, default=str)})
        s._audit_saved = len(s.trace)
