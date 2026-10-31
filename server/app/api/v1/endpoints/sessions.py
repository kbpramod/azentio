"""VaaniDesk voice/chat sessions. Forwards to the AI orchestration service.

Frontend flow: POST /sessions -> POST /sessions/{id}/turn (text or audio) ... -> POST /sessions/{id}/end
Verification happens inside the conversation (caller says customer ID + date of birth).
"""
from fastapi import APIRouter, Request

from app.integrations.ai_pipeline import forward

router = APIRouter()


@router.post("", summary="Start a voice/chat session (returns greeting)")
async def start_session():
    return await forward("POST", "/sessions")


@router.get("", summary="List sessions (ops dashboard)")
async def list_sessions():
    return await forward("GET", "/sessions")


@router.get("/{session_id}", summary="Session transcript, tickets, escalation and audit trace")
async def get_session(session_id: str):
    return await forward("GET", f"/sessions/{session_id}")


@router.post("/{session_id}/turn", summary="Send one customer turn as JSON {text} or multipart audio")
async def turn(session_id: str, request: Request):
    if request.headers.get("content-type", "").startswith("multipart/form-data"):
        form = await request.form()
        audio = form.get("audio")
        files = {"audio": (audio.filename or "audio.webm", await audio.read(),
                           audio.content_type or "application/octet-stream")}
        return await forward("POST", f"/sessions/{session_id}/turn", files=files,
                             data={"lang": str(form.get("lang") or "en")})
    return await forward("POST", f"/sessions/{session_id}/turn", json=await request.json())


@router.post("/{session_id}/escalate", summary="Customer pressed 'Talk to a human'")
async def escalate(session_id: str):
    return await forward("POST", f"/sessions/{session_id}/escalate")


@router.post("/{session_id}/end", summary="End the call")
async def end(session_id: str):
    return await forward("POST", f"/sessions/{session_id}/end")
