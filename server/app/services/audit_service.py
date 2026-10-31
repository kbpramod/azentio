import re
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.vaani_models import AuditEvent


SENSITIVE_KEYS = {"password", "secret", "token", "dob", "date_of_birth", "pin", "otp", "ssn", "cvv"}


def sanitize_metadata(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not data:
        return {}
    sanitized = {}
    for key, value in data.items():
        lower_key = key.lower()
        if any(s in lower_key for s in SENSITIVE_KEYS):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, str) and ("acc-" in value.lower() or "az-" in value.lower()) and len(value) > 6:
            # Mask bank account identifiers partially: e.g. AZ-882194 -> ****2194
            sanitized[key] = f"****{value[-4:]}"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_metadata(value)
        else:
            sanitized[key] = value
    return sanitized


async def record_audit_event(
    db: AsyncSession,
    event_type: str,
    event_status: str = "SUCCESS",
    session_id: Optional[str] = None,
    call_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AuditEvent:
    safe_data = sanitize_metadata(metadata)
    event = AuditEvent(
        session_id=session_id,
        call_id=call_id,
        event_type=event_type,
        event_status=event_status,
        safe_metadata=safe_data,
    )
    db.add(event)
    await db.flush()
    return event

