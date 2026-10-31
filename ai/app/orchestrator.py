"""Orchestrator: one customer turn in, one grounded reply out.

text -> NLU -> state/context update -> policy -> tools -> template reply -> grounding guard -> TTS
"""
import time
from dataclasses import dataclass, field

from . import config, kb, nlu as nlu_mod, policy, tts
from .responder import (CLAIM_STATUS_TEXT, STAGE_TEXT, TICKET_STATUS_TEXT, TXN_STATUS_TEXT,
                        inr, say_date, ungrounded_numbers)
from .schemas import (DATA_INTENTS, Escalation, IntentName, NLUResult, Source, TicketRef,
                      TurnResponse)
from .state import Session, State
from .tools import NotVerified, Tools, make_backend

GREETING = ("Hello, I'm the virtual service assistant. This call is handled by an AI assistant and may be recorded. "
            "You can ask for a human at any time. How can I help you today?")
SAFE_FALLBACK = "I'm sorry, I couldn't confirm that from our records, so I'm connecting you to a colleague."

INTENT_LABEL = {
    IntentName.repayment_schedule: "repayment schedule",
    IntentName.loan_statement: "loan statement",
}


@dataclass
class TurnCtx:
    text: str
    nlu: NLUResult
    replies: list = field(default_factory=list)
    sources: list = field(default_factory=list)
    payloads: list = field(default_factory=list)
    new_tickets: list = field(default_factory=list)
    verify_result: object = None  # None = not tried this turn

    def say(self, line: str):
        self.replies.append(line)

    def used(self, system: str, ref: str, payload):
        self.sources.append(Source(system=system, ref=ref))
        self.payloads.append(payload)


def _ms(t0):
    return int((time.perf_counter() - t0) * 1000)


class Orchestrator:
    def __init__(self, backend=None):
        self.backend = backend or make_backend()

    # ------------------------------------------------------------ entry points

    def greet(self, s: Session) -> str:
        s.add_turn("agent", GREETING)
        s.audit("GREET", {})
        return GREETING

    def handle_low_confidence(self, s: Session, transcript: str, conf: float, latency: dict) -> TurnResponse:
        s.low_conf_count += 1
        s.audit("STT", {"confidence": round(conf, 2), "action": "ask_repeat"})
        reply = ("Sorry, I didn't catch that clearly. Could you please say it again?" if s.low_conf_count < 2
                 else "Sorry, I'm still having trouble hearing you. You can also type your question in the box below.")
        s.add_turn("agent", reply)
        return self._response(s, transcript, conf, [], reply, [], [], latency)

    def handle_text(self, s: Session, text: str, stt_conf=None, latency=None) -> TurnResponse:
        latency = dict(latency or {})
        s.add_turn("customer", text)

        t0 = time.perf_counter()
        nlu = nlu_mod.parse(text, s.context_summary())
        latency["nlu"] = _ms(t0)
        s.audit("NLU", {"source": nlu.source, "intents": ",".join(i.name.value for i in nlu.intents),
                        "sentiment": nlu.sentiment})

        ctx = TurnCtx(text=text, nlu=nlu)
        t1 = time.perf_counter()
        tools = Tools(self.backend, s)
        try:
            self._process(s, ctx, tools)
        except Exception as exc:  # upstream/tool error: apologise + log ticket, never crash
            s.audit("ERROR", {"error": type(exc).__name__})
            ctx.replies = ["I'm sorry, I'm having trouble reaching our systems right now."]
            try:
                t = tools.create_ticket("fallback", "system_error", f"System error while handling: {text[:120]}")
                self._record_ticket(s, ctx, t)
                ctx.say(f"I've logged your request with reference {t['ticket_id']} and our team will follow up.")
            except Exception:
                pass
        latency["tools"] = _ms(t1)

        reply = " ".join(ctx.replies) or "How else can I help you?"
        bad = ungrounded_numbers(reply, ctx.payloads, extra_allowed=self._allowed_extra(s, ctx))
        if bad:
            s.audit("GUARD", {"ok": False, "ungrounded": str(bad)})
            reply = SAFE_FALLBACK
            self._escalate(s, ctx, "grounding_guard", "NORMAL")
        else:
            s.audit("GUARD", {"ok": True})

        s.add_turn("agent", reply)
        return self._response(s, text, stt_conf, nlu.intents, reply, ctx.sources, ctx.new_tickets, latency)

    # ------------------------------------------------------------ core logic

    def _process(self, s: Session, ctx: TurnCtx, tools: Tools):
        nlu, e = ctx.nlu, ctx.nlu.entities
        names = [i.name for i in nlu.intents]

        if s.state == State.CLOSED:
            ctx.say("This call has ended. Please start a new call if you need more help.")
            return

        # identity details offered this turn (only before verification)
        if not s.verified:
            if e.customer_id:
                s.customer_id = e.customer_id
            if e.dob:
                s.dob = e.dob

        # product memory + corrections ("no, I meant my vehicle loan")
        redo = []
        if e.product:
            if nlu.is_correction and s.last_data_intent and e.product != s.active_product:
                ctx.say(f"Got it, your {e.product} loan.")
                redo = [s.last_data_intent]
            s.active_product = e.product

        # escalation triggers checked before anything else
        trig = policy.escalation_trigger(nlu)

        work = []
        for n in redo + s.pending_intents + names:
            if n not in work and n != IntentName.provide_info:
                work.append(n)
        s.pending_intents = []

        data_count = sum(1 for n in work if n in DATA_INTENTS)
        if data_count > 1 and not s.verified and s.state != State.LOCKED:
            ctx.say("I can help with both of those.")

        for intent in work:
            if intent == IntentName.goodbye:
                continue
            if policy.needs_verification(intent):
                if not self._ensure_verified(s, ctx, tools):
                    if s.state != State.LOCKED:
                        s.pending_intents.append(intent)
                    continue
            handler = getattr(self, f"_do_{intent.value}", None)
            if handler is None:
                continue
            try:
                handler(s, ctx, tools)
            except NotVerified:
                s.pending_intents.append(intent)

        # only identity details this turn -> verify now even with no pending work
        if not work and not s.verified and s.customer_id:
            if self._ensure_verified(s, ctx, tools) and ctx.verify_result:
                ctx.say("How can I help you today?")

        if trig and s.escalation is None:
            self._escalate(s, ctx, *trig)

        if IntentName.goodbye in names and not s.pending_intents:
            if not ctx.replies:
                ctx.say("Thank you for calling. Goodbye.")
            else:
                ctx.say("Thank you for calling.")
            s.state = State.CLOSED
            s.audit("CLOSE", {})
        elif not ctx.replies:
            ctx.say("I'm sorry, could you tell me a little more about what you need?")

    def _ensure_verified(self, s: Session, ctx: TurnCtx, tools: Tools) -> bool:
        if s.verified:
            return True
        if ctx.verify_result is not None:
            return bool(ctx.verify_result)
        if s.state == State.LOCKED:
            ctx.verify_result = False
            ctx.say("For your security I can't share account details on this call. A colleague will help you.")
            return False
        if not s.customer_id:
            s.state = State.IDENTIFY
            ctx.say("First I need to verify your identity. Please tell me your customer ID.")
            ctx.verify_result = False
            return False
        if not s.dob:
            s.state = State.VERIFY
            ctx.say("Thank you. To verify you, please tell me your date of birth.")
            ctx.verify_result = False
            return False

        ok = tools.verify(s.customer_id, s.dob)
        ctx.verify_result = ok
        if ok:
            s.verified = True
            s.state = State.ACT
            cust = self.backend.customer(s.customer_id) or {}
            s.customer_name = cust.get("name")
            ctx.say(f"Thank you{', ' + s.customer_name if s.customer_name else ''}. You're verified.")
            return True

        s.attempts_left -= 1
        s.customer_id, s.dob = None, None
        if s.attempts_left <= 0:
            s.state = State.LOCKED
            ctx.say("Those details still don't match our records. For your security I can't share any account details.")
            self._escalate(s, ctx, "auth_failed", "NORMAL")
        else:
            s.state = State.IDENTIFY
            ctx.say("Those details don't match our records. Please tell me your customer ID and date of birth again.")
        return False

    # ------------------------------------------------------------ helpers

    def _pick(self, items, product, s, ctx, intent, kind="loan"):
        """Choose one record by product; ask to clarify when ambiguous. Returns record or None."""
        if product:
            items = [i for i in items if i.get("product") == product]
        if len(items) > 1:
            options = " or ".join(f"your {i['product']} {kind}" for i in items)
            ctx.say(f"Do you mean {options}?")
            s.pending_intents.append(intent)
            s.state = State.CLARIFY
            return None
        return items[0] if items else None

    def _record_ticket(self, s, ctx, t):
        ref = TicketRef(ticket_id=t["ticket_id"], type=t["type"], category=t.get("category"), status=t.get("status", "OPEN"))
        s.tickets.append(ref)
        ctx.new_tickets.append(ref)
        ctx.payloads.append(t)

    def _escalate(self, s: Session, ctx: TurnCtx, reason: str, priority: str):
        intents = [i.name.value for i in ctx.nlu.intents]
        said = [t["text"] for t in s.turns if t["speaker"] == "customer"]
        s.escalation = Escalation(
            reason=reason, priority=priority,
            summary=f"Customer {s.customer_id if s.verified else '(not verified)'}: \"{said[-1][:160] if said else ''}\"",
            intents=intents,
            steps_tried=[f"{x['stage']}:{x.get('tool', x.get('action', ''))}" for x in s.trace[-6:]],
            ticket_id=s.tickets[-1].ticket_id if s.tickets else None,
        )
        s.state = State.ESCALATED
        s.audit("ESCALATE", {"reason": reason, "priority": priority})
        ctx.say("I'm connecting you to a colleague now. They will see everything we discussed, so you won't need to repeat yourself.")

    def _allowed_extra(self, s, ctx):
        return {s.attempts_left, config.MAX_AUTH_ATTEMPTS}

    # ------------------------------------------------------------ intent handlers (data from tools only)

    def _do_loan_status(self, s, ctx, tools):
        apps = tools.applications()
        app = self._pick(apps, s.active_product, s, ctx, IntentName.loan_status, "loan application")
        if app is None:
            if not s.pending_intents:
                ctx.say("I couldn't find a loan application on your profile.")
            return
        s.last_data_intent = IntentName.loan_status
        s.active_product = s.active_product or app["product"]
        ctx.used("LOS", app["app_id"], app)
        line = f"Your {app['product']} loan application for {inr(app['amount'])} {STAGE_TEXT.get(app['stage'], 'is being processed')}."
        if app.get("pending_items"):
            line += f" We are waiting for: {', '.join(app['pending_items'])}."
        ctx.say(line)

    def _do_emi_enquiry(self, s, ctx, tools):
        loans = tools.loans()
        if s.active_product and not any(l["product"] == s.active_product for l in loans):
            loans = []
        if not loans:
            apps = [a for a in tools.applications() if not s.active_product or a["product"] == s.active_product]
            s.last_data_intent = IntentName.emi_enquiry
            if apps:
                ctx.used("LOS", apps[0]["app_id"], apps[0])
                ctx.say("Your first instalment will be scheduled only after the loan is approved and disbursed, so there is no due date yet.")
            else:
                ctx.say("I couldn't find an active loan" + (f" of type {s.active_product}" if s.active_product else "") + " on your profile.")
            return
        loan = self._pick(loans, s.active_product, s, ctx, IntentName.emi_enquiry)
        if loan is None:
            return
        s.last_data_intent = IntentName.emi_enquiry
        s.active_product = loan["product"]
        ctx.used("LMS", loan["loan_id"], loan)
        line = (f"Your {loan['product']} loan instalment is {inr(loan['emi_amount'])}, due on {say_date(loan['next_due_date'])}. "
                f"The outstanding balance is {inr(loan['outstanding'])}.")
        if loan.get("overdue_amount"):
            line += f" You also have an overdue amount of {inr(loan['overdue_amount'])} from an earlier instalment, which is separate from the upcoming one."
        ctx.say(line)

    def _document_request(self, s, ctx, tools, intent):
        label = INTENT_LABEL[intent]
        loans = tools.loans()
        target = self._pick(loans, s.active_product, s, ctx, intent) if loans else None
        if loans and target is None:
            return
        if target is None:
            apps = [a for a in tools.applications() if not s.active_product or a["product"] == s.active_product]
            target = apps[0] if apps else None
        ref = (target or {}).get("loan_id") or (target or {}).get("app_id") or "profile"
        product = (target or {}).get("product")
        t = tools.create_ticket("service_request", intent.value,
                                f"Customer requested {label} for {ref}" + (f" ({product} loan)" if product else ""))
        self._record_ticket(s, ctx, t)
        if target:
            ctx.payloads.append(target)
        ctx.say(f"I've raised a request for your {label}" + (f" for your {product} loan" if product else "") +
                f". Your reference number is {t['ticket_id']}. Our team will send it to your registered contact details.")

    def _do_repayment_schedule(self, s, ctx, tools):
        self._document_request(s, ctx, tools, IntentName.repayment_schedule)

    def _do_loan_statement(self, s, ctx, tools):
        self._document_request(s, ctx, tools, IntentName.loan_statement)

    def _do_account_balance(self, s, ctx, tools):
        accts = tools.accounts()
        if not accts:
            ctx.say("I couldn't find a bank account on your profile.")
            return
        a = accts[0]
        ctx.used("CBS", a["account_id"], a)
        ctx.say(f"Your {a['type']} account ending {a['account_id'][-4:]} has a balance of {inr(a['balance'])}.")

    def _do_transaction_status(self, s, ctx, tools):
        txns = tools.transactions()
        e = ctx.nlu.entities
        if e.txn_id:
            txns = [t for t in txns if t["txn_id"] == e.txn_id]
        if not txns:
            ctx.say("I couldn't find that transaction on your account.")
            return
        t = sorted(txns, key=lambda x: x["date"])[-1]
        ctx.used("CBS", t["txn_id"], t)
        ctx.say(f"Your {t['direction']} of {inr(t['amount'])} on {say_date(t['date'])} to {t['merchant']} "
                f"{TXN_STATUS_TEXT.get(t['status'], 'has status ' + t['status'])}.")

    def _do_ticket_status(self, s, ctx, tools):
        tid = ctx.nlu.entities.ticket_id
        t = tools.get_ticket(tid) if tid else None
        if t is None and not tid:
            mine = tools.tickets()
            t = mine[-1] if mine else None
        if t is None:
            ctx.say("I couldn't find that request on your profile.")
            return
        ctx.used("CSM", t["ticket_id"], t)
        ctx.say(f"Your request {t['ticket_id']} about {t.get('category', 'your issue').replace('_', ' ')} is "
                f"{TICKET_STATUS_TEXT.get(t['status'], t['status'].lower())}.")

    def _do_policy_enquiry(self, s, ctx, tools):
        pols = tools.policies()
        if not pols:
            ctx.say("I couldn't find an insurance policy on your profile.")
            return
        p = pols[0]
        ctx.used("INS", p["policy_id"], p)
        ctx.say(f"Your {p['type']} policy is {p['status'].lower()}. The next premium of {inr(p['premium'])} "
                f"is due on {say_date(p['premium_due'])}.")

    def _do_claim_status(self, s, ctx, tools):
        claims = tools.claims()
        if not claims:
            ctx.say("I couldn't find an insurance claim on your profile.")
            return
        c = claims[-1]
        ctx.used("INS", c["claim_id"], c)
        ctx.say(f"Your claim filed on {say_date(c['filed_on'])} {CLAIM_STATUS_TEXT.get(c['status'], 'has status ' + c['status'])}.")

    def _do_complaint(self, s, ctx, tools):
        cat = ctx.nlu.entities.complaint_category or "service_quality"
        sensitive = cat in policy.SENSITIVE_COMPLAINTS
        t = tools.create_ticket("complaint", cat, f"Complaint: {ctx.text[:200]}",
                                priority="HIGH" if sensitive else "NORMAL",
                                escalated=sensitive, reason="sensitive_intent" if sensitive else None)
        self._record_ticket(s, ctx, t)
        ctx.say(f"I'm sorry about this. I've registered your complaint. Your reference number is {t['ticket_id']}.")

    def _do_faq(self, s, ctx, tools):
        hit = kb.search(ctx.text)
        if hit is None:
            self._do_unknown(s, ctx, tools)
            return
        ctx.used("KB", hit["id"], hit)
        ctx.say(hit["answer"])

    def _do_human_handoff(self, s, ctx, tools):
        pass  # handled by escalation trigger

    def _do_third_party_request(self, s, ctx, tools):
        s.audit("REFUSE", {"action": "third_party_request"})
        ctx.say("I'm sorry, I can only share details with the verified account holder, so I can't help with someone else's account.")

    def _do_unauthorised_action(self, s, ctx, tools):
        s.audit("REFUSE", {"action": "unauthorised_action"})
        t = tools.create_ticket("service_request", "review_request", f"Customer asked: {ctx.text[:200]}")
        self._record_ticket(s, ctx, t)
        ctx.say(f"I'm not able to do that myself, but I've raised a request for our team to review it. "
                f"Your reference number is {t['ticket_id']}.")

    def _do_unknown(self, s, ctx, tools):
        s.audit("FALLBACK", {"action": "unknown_request"})
        t = tools.create_ticket("fallback", "out_of_scope", f"Unsupported request: {ctx.text[:200]}",
                                escalated=True, reason="out_of_scope")
        self._record_ticket(s, ctx, t)
        ctx.say(f"I'm sorry, I can't help with that here and I don't want to guess. I've logged your question "
                f"as {t['ticket_id']} and a member of our team will contact you.")

    # ------------------------------------------------------------ response

    def _response(self, s, transcript, conf, intents, reply, sources, tickets, latency) -> TurnResponse:
        t0 = time.perf_counter()
        audio_url = tts.synthesize(reply, s.id, len(s.turns))
        latency["tts"] = _ms(t0)
        return TurnResponse(
            session_id=s.id, transcript=transcript, stt_confidence=conf, intents=intents, state=s.state,
            verified=s.verified, reply_text=reply, reply_audio_url=audio_url, sources=sources,
            tickets=tickets, escalation=s.escalation if s.state == State.ESCALATED else None, latency_ms=latency,
        )
