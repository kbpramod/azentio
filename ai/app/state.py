"""Conversation state machine + session memory.

States: GREET -> IDENTIFY -> VERIFY -> ACT -> (CLARIFY) -> ESCALATED / CLOSED
In-memory store is fine for Level 1; Member B can persist via GET /sessions/{id}.
"""
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from . import config
from .schemas import Escalation, IntentName


class State:
    GREET = "GREET"
    IDENTIFY = "IDENTIFY"    # need customer ID
    VERIFY = "VERIFY"        # have ID, need DOB
    ACT = "ACT"
    CLARIFY = "CLARIFY"      # waiting for missing detail (e.g. which loan)
    ESCALATED = "ESCALATED"
    LOCKED = "LOCKED"        # auth failed too often
    CLOSED = "CLOSED"


def _mask(value: str) -> str:
    """Mask digits in long identifiers for logs (keep last 4)."""
    return re.sub(r"\d{5,}", lambda m: "*" * (len(m.group()) - 4) + m.group()[-4:], value)


@dataclass
class Session:
    id: str = field(default_factory=lambda: "S-" + uuid.uuid4().hex[:6])
    state: str = State.GREET
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    dob: Optional[str] = None
    verified: bool = False
    attempts_left: int = config.MAX_AUTH_ATTEMPTS
    active_product: Optional[str] = None
    pending_intents: list = field(default_factory=list)     # IntentName waiting on auth/clarification
    last_data_intent: Optional[IntentName] = None            # for corrections ("no, vehicle loan")
    turns: list = field(default_factory=list)                # {"speaker","text",...}
    tickets: list = field(default_factory=list)
    escalation: Optional[Escalation] = None
    trace: list = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    low_conf_count: int = 0

    def audit(self, stage: str, detail: dict):
        safe = {k: _mask(v) if isinstance(v, str) else v for k, v in detail.items()}
        self.trace.append({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "stage": stage, **safe})

    def add_turn(self, speaker: str, text: str, **extra):
        self.turns.append({"speaker": speaker, "text": text, **extra})

    def context_summary(self) -> str:
        """Short context handed to the NLU so follow-ups ('send me that') resolve."""
        last = [f"{t['speaker']}: {t['text']}" for t in self.turns[-4:]]
        return (f"verified={self.verified}; active_product={self.active_product}; "
                f"pending={[i.value for i in self.pending_intents]}; recent=" + " | ".join(last))


SESSIONS: dict[str, Session] = {}


def new_session() -> Session:
    s = Session()
    SESSIONS[s.id] = s
    return s
