"""Grounded response helpers.

Replies are built from templates filled ONLY with tool data, then checked by the grounding guard:
every number in the reply must appear in the tool payloads for this turn. If not, the reply is blocked.
"""
import re
from datetime import date

STAGE_TEXT = {
    "SUBMITTED": "has been received and is waiting for review. It is not approved yet",
    "DOC_VERIFICATION": "is awaiting document verification. It is not approved yet",
    "CREDIT_REVIEW": "is under credit review. It is not approved yet",
    "APPROVED": "has been approved",
    "REJECTED": "was not approved",
    "DISBURSED": "has been approved and the amount has been disbursed",
}

TXN_STATUS_TEXT = {
    "SUCCESS": "was completed successfully",
    "PENDING": "is still pending. I don't have information on why it is pending",
    "FAILED": "is recorded as failed. I don't have information on the reason",
}

TICKET_STATUS_TEXT = {"OPEN": "open", "IN_PROGRESS": "in progress", "RESOLVED": "resolved", "CLOSED": "closed"}

CLAIM_STATUS_TEXT = {
    "SUBMITTED": "has been submitted and is waiting for review",
    "UNDER_REVIEW": "is under review. I can't confirm whether it will be approved",
    "APPROVED": "has been approved",
    "REJECTED": "was not approved",
}


def inr(n: int) -> str:
    """Indian digit grouping: 412300 -> ₹4,12,300."""
    s = str(int(n))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(\d)(?=(\d{2})+$)", r"\1,", head)
        s = f"{head},{tail}"
    return f"₹{s}"


def say_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {d.strftime('%B')} {d.year}"


def _numbers_in(obj, out: set):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out.add(int(obj))
    elif isinstance(obj, str):
        out.update(int(x) for x in re.findall(r"\d+", obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            _numbers_in(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _numbers_in(v, out)


def ungrounded_numbers(reply: str, payloads: list, extra_allowed=()) -> list[int]:
    """Numbers in the reply that do not come from any tool payload. Empty list = grounded."""
    allowed: set[int] = set(extra_allowed)
    _numbers_in(payloads, allowed)
    found = [int(x.replace(",", "")) for x in re.findall(r"\d[\d,]*", reply)]
    return [n for n in found if n not in allowed]
