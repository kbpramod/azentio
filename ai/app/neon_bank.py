"""Banking backend that reads/writes the shared Neon Postgres database (synthetic data).

Same method names and return shapes as MockBank, so the orchestrator doesn't change.
Tables are documented in server/DB_SCHEMA.md and created by the seed script.
Also records calls, turns and audit events for the ops dashboard.
"""
import json
import threading
import time
from datetime import date, datetime

import psycopg
from psycopg.rows import dict_row

from . import config


# the server seed uses different product names; the agent speaks in personal / vehicle / home
PRODUCT_ALIASES = {"home_loan": "home", "housing": "home", "auto_loan": "vehicle", "car": "vehicle",
                   "vehicle_loan": "vehicle", "personal_loan": "personal"}


def _clean(row: dict | None, source: str) -> dict | None:
    if row is None:
        return None
    out = {}
    for k, v in row.items():
        out[k] = v.isoformat() if isinstance(v, (date, datetime)) else v
    if isinstance(out.get("product"), str):
        out["product"] = PRODUCT_ALIASES.get(out["product"].lower(), out["product"].lower())
    for k in ("amount", "outstanding", "emi_amount", "overdue_amount", "principal", "balance", "premium"):
        if isinstance(out.get(k), float) and out[k].is_integer():
            out[k] = int(out[k])  # server seed stores some amounts as floats
    out["source"] = source
    return out


class NeonBank:
    def __init__(self, url: str | None = None):
        self.url = url or config.DATABASE_URL
        if not self.url:
            raise RuntimeError("DATABASE_URL is not set (ai/.env)")
        self._conn = None
        self._lock = threading.Lock()
        self._cache = {}  # customer_id -> (loaded_at, profile)

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

    def warm(self):
        """Open the database connection at startup (the first connect to Neon takes ~1.5 s)."""
        try:
            self._q("SELECT 1", one=True)
        except Exception:
            pass

    # --- one round trip loads everything the agent may need about a verified customer.
    # Cached for the rest of the call: the database is in another region (~0.25 s per query).
    PROFILE_SQL = """
        SELECT c.name,
          (SELECT COALESCE(json_agg(a ORDER BY a.applied_on DESC), '[]') FROM loan_applications a
             WHERE a.customer_id = c.customer_id) AS applications,
          (SELECT COALESCE(json_agg(l ORDER BY l.loan_id), '[]') FROM loans l
             WHERE l.customer_id = c.customer_id AND l.status = 'ACTIVE') AS loans,
          (SELECT COALESCE(json_agg(ac ORDER BY ac.account_id), '[]') FROM accounts ac
             WHERE ac.customer_id = c.customer_id) AS accounts,
          (SELECT COALESCE(json_agg(t ORDER BY t.date), '[]') FROM bank_transactions t
             JOIN accounts ac USING (account_id) WHERE ac.customer_id = c.customer_id) AS transactions,
          (SELECT COALESCE(json_agg(p ORDER BY p.policy_id), '[]') FROM policies p
             WHERE p.customer_id = c.customer_id) AS policies,
          (SELECT COALESCE(json_agg(cl ORDER BY cl.filed_on), '[]') FROM claims cl
             JOIN policies p USING (policy_id) WHERE p.customer_id = c.customer_id) AS claims,
          (SELECT COALESCE(json_agg(tk ORDER BY tk.created_at), '[]') FROM tickets tk
             WHERE tk.customer_id = c.customer_id) AS tickets
        FROM customers c WHERE c.customer_id = %(cid)s {extra}"""
    PROFILE_TTL = 120  # seconds
    SOURCES = {"applications": "LOS-SIMULATED", "loans": "LMS-SIMULATED", "accounts": "CBS-SIMULATED",
               "transactions": "CBS-SIMULATED", "policies": "INS-SIMULATED", "claims": "INS-SIMULATED",
               "tickets": "CSM-SIMULATED"}



    def _store(self, customer_id, row):
        prof = {"name": row["name"]}
        for k, src in self.SOURCES.items():
            prof[k] = [_clean(r, src) for r in (row[k] or [])]
        self._cache[customer_id] = (time.monotonic(), prof)
        return prof

    def _profile(self, customer_id):
        hit = self._cache.get(customer_id)
        if hit and time.monotonic() - hit[0] < self.PROFILE_TTL:
            return hit[1]
        row = self._q(self.PROFILE_SQL.format(extra=""), {"cid": customer_id}, one=True)
        return self._store(customer_id, row) if row else {"name": None, **{k: [] for k in self.SOURCES}}

    # --- auth: verifies AND preloads the profile in the same round trip
    def verify(self, customer_id, dob):
        row = self._q(self.PROFILE_SQL.format(extra="AND c.dob = %(dob)s"),
                      {"cid": customer_id, "dob": dob}, one=True)
        if row is None:
            return False
        self._store(customer_id, row)
        return True

    def customer(self, customer_id):
        hit = self._cache.get(customer_id)
        if hit:
            return {"customer_id": customer_id, "name": hit[1]["name"], "source": "CORE-SIMULATED"}
        return _clean(self._q("SELECT customer_id, name FROM customers WHERE customer_id=%s",
                              (customer_id,), one=True), "CORE-SIMULATED")

    # --- LOS / LMS / CBS / INS (served from the profile)
    def applications(self, customer_id):
        return self._profile(customer_id)["applications"]

    def loans(self, customer_id):
        return self._profile(customer_id)["loans"]

    def accounts(self, customer_id):
        return self._profile(customer_id)["accounts"]

    def transactions(self, customer_id):
        return self._profile(customer_id)["transactions"]

    def policies(self, customer_id):
        return self._profile(customer_id)["policies"]

    def claims(self, customer_id):
        return self._profile(customer_id)["claims"]

    # --- CSM tickets
    TICKET_COLS = ("customer_id", "type", "category", "priority", "summary", "escalated",
                   "escalation_reason", "call_id", "idempotency_key")

    def create_ticket(self, payload: dict) -> dict:
        """One round trip: return the existing ticket for this idempotency key, or insert the next number."""
        prefix = "CMP" if payload["type"] == "complaint" else "SR"
        start = 2210 if prefix == "CMP" else 4471
        cols = ", ".join(self.TICKET_COLS)
        vals = ", ".join(f"%({c})s" for c in self.TICKET_COLS)
        sql = f"""
            WITH existing AS (SELECT * FROM tickets WHERE idempotency_key = %(idempotency_key)s),
            nxt AS (  -- other services use non-numeric IDs (e.g. SR-5F234A); count numeric ones only
              SELECT GREATEST(%(start)s, COALESCE(MAX(split_part(ticket_id, '-', 2)::int) + 1, %(start)s)) AS n
              FROM tickets WHERE ticket_id ~ %(pattern)s),
            ins AS (
              INSERT INTO tickets (ticket_id, {cols})
              SELECT %(prefix)s || '-' || n, {vals} FROM nxt
              WHERE NOT EXISTS (SELECT 1 FROM existing)
              RETURNING *)
            SELECT * FROM ins UNION ALL SELECT * FROM existing"""
        params = {**{c: payload.get(c) for c in self.TICKET_COLS},
                  "start": start, "pattern": f"^{prefix}-[0-9]+$", "prefix": prefix}
        for _ in range(5):  # retry if two calls grab the same number at once
            try:
                ticket = _clean(self._q(sql, params, one=True), "CSM-SIMULATED")
                break
            except psycopg.errors.UniqueViolation:
                continue
        else:
            raise RuntimeError("could not allocate ticket id")
        cid = payload.get("customer_id")
        if cid in self._cache and all(t["ticket_id"] != ticket["ticket_id"] for t in self._cache[cid][1]["tickets"]):
            self._cache[cid][1]["tickets"].append(ticket)
        return ticket

    def get_ticket(self, ticket_id):
        for _, prof in self._cache.values():
            for t in prof["tickets"]:
                if t["ticket_id"] == ticket_id:
                    return t
        return _clean(self._q("SELECT * FROM tickets WHERE ticket_id=%s", (ticket_id,), one=True), "CSM-SIMULATED")

    def tickets_for(self, customer_id):
        return self._profile(customer_id)["tickets"]

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
