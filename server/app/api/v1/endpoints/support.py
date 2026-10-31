import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

logger = logging.getLogger("azentio.support")

router = APIRouter()

# Directory to temporarily stage received voice clips
UPLOAD_DIR = Path(__file__).resolve().parents[4] / "uploads" / "support_voice"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class TextSupportRequest(BaseModel):
    message: str
    customer_name: Optional[str] = "Customer"
    account_number: Optional[str] = None
    category: Optional[str] = "General Inquiry"


class SupportTicketResponse(BaseModel):
    status: str
    ticket_id: str
    type: str
    message: str
    filename: Optional[str] = None
    size_bytes: Optional[int] = None
    received_at: str


@router.post(
    "/voice",
    response_model=SupportTicketResponse,
    summary="Receive voice note from customer support widget",
)
async def receive_voice_support(
    audio_file: Optional[UploadFile] = File(None),
    file: Optional[UploadFile] = File(None),
    customer_name: Optional[str] = Form(None),
    account_number: Optional[str] = Form(None),
    note: Optional[str] = Form(None),
) -> SupportTicketResponse:
    """
    Accepts voice recording from the frontend support widget.
    Acknowledges receipt immediately ('received' status) for future processing.
    """
    target_file = audio_file or file
    if target_file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No audio file was uploaded. Please provide an audio recording.",
        )

    # Read binary contents
    content = await target_file.read()
    size_bytes = len(content)

    ticket_id = f"SUP-V-{uuid.uuid4().hex[:8].upper()}"
    received_time = datetime.now(timezone.utc).isoformat()

    # Save audio file to storage for future backend processing
    safe_filename = f"{ticket_id}_{target_file.filename or 'voice.webm'}"
    dest_path = UPLOAD_DIR / safe_filename
    try:
        with open(dest_path, "wb") as f:
            f.write(content)
        logger.info(
            f"[Support Desk] Voice note {ticket_id} received from {customer_name or 'Guest'} "
            f"({size_bytes} bytes). Saved to {dest_path.name}"
        )
    except Exception as exc:
        logger.warning(f"Could not persist voice file to disk: {exc}")

    return SupportTicketResponse(
        status="received",
        ticket_id=ticket_id,
        type="voice",
        message="Voice note received successfully. Azentio Priority Support has registered your audio dispatch.",
        filename=target_file.filename or "recording.webm",
        size_bytes=size_bytes,
        received_at=received_time,
    )


@router.post(
    "/text",
    response_model=SupportTicketResponse,
    summary="Receive typed customer support request",
)
async def receive_text_support(payload: TextSupportRequest) -> SupportTicketResponse:
    """
    Accepts typed support inquiry from the frontend widget.
    Acknowledges receipt immediately ('received' status).
    """
    if not payload.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Support message cannot be empty.",
        )

    ticket_id = f"SUP-T-{uuid.uuid4().hex[:8].upper()}"
    received_time = datetime.now(timezone.utc).isoformat()

    logger.info(
        f"[Support Desk] Text inquiry {ticket_id} received from {payload.customer_name} "
        f"(Account: {payload.account_number or 'N/A'}, Category: {payload.category}): {payload.message[:80]}..."
    )

    return SupportTicketResponse(
        status="received",
        ticket_id=ticket_id,
        type="text",
        message="Support message received successfully. Azentio Priority Support will review and assist you shortly.",
        received_at=received_time,
    )


@router.get("/status", summary="Support desk online status")
async def get_support_status():
    return {
        "status": "online",
        "desk": "Azentio 24/7 Priority Concierge",
        "voice_support_enabled": True,
        "average_response_mins": 2,
    }

