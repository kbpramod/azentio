"""FastAPI app. Run: uvicorn app.main:app --reload --port 8001   then open http://localhost:8001/docs"""
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config, stt
from .orchestrator import Orchestrator
from .schemas import Escalation, TurnResponse
from .state import SESSIONS, State, new_session
from .tts import AUDIO_DIR

app = FastAPI(title="VaaniDesk AI Backend (Member 2)", version="0.1.0",
              description="AI orchestration, voice and evaluation. Banking systems are SIMULATED.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
AUDIO_DIR.mkdir(exist_ok=True)
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

orch = Orchestrator()


@app.on_event("startup")
def _load_stt():
    stt.warm_up()


def _err(status, code, message, retryable=False):
    raise HTTPException(status, detail={"error": {"code": code, "message": message, "retryable": retryable}})


def _session(sid):
    s = SESSIONS.get(sid)
    if not s:
        _err(404, "NOT_FOUND", "Unknown session")
    return s


@app.get("/health")
def health():
    return {"ok": True, "nlu_mode": config.NLU_MODE, "banking": config.BANK_BACKEND,
            "tts": config.TTS_PROVIDER}


@app.post("/api/v1/sessions")
def start_session():
    s = new_session()
    return {"session_id": s.id, "state": s.state, "reply_text": orch.greet(s), "reply_audio_url": None}


@app.post("/api/v1/sessions/{sid}/turn", response_model=TurnResponse)
async def turn(sid: str, request: Request):
    """JSON {"text": "..."}  OR  multipart/form-data with field `audio` (wav/webm/mp3/ogg)."""
    s = _session(sid)
    ctype = request.headers.get("content-type", "")
    if ctype.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("audio")
        if upload is None:
            _err(400, "BAD_AUDIO", "Missing form field 'audio'")
        t0 = time.perf_counter()
        try:
            text, conf = stt.transcribe_bytes(await upload.read(), upload.filename or "audio.webm",
                                              str(form.get("lang") or "en"))
        except stt.STTError as exc:
            _err(422, "BAD_AUDIO", str(exc), retryable=True)
        latency = {"stt": int((time.perf_counter() - t0) * 1000)}
        s.audit("STT", {"confidence": conf, "chars": len(text)})
        if not text or conf < config.STT_MIN_CONFIDENCE:
            return orch.handle_low_confidence(s, text, conf, latency)
        return orch.handle_text(s, text, stt_conf=conf, latency=latency)

    body = await request.json()
    text = (body.get("text") or "").strip()
    if not text:
        _err(400, "EMPTY_INPUT", "Provide 'text' or an audio file")
    return orch.handle_text(s, text)


@app.post("/api/v1/sessions/{sid}/escalate")
def escalate(sid: str):
    s = _session(sid)
    s.escalation = s.escalation or Escalation(reason="user_asks_human", summary="Customer pressed 'Talk to a human'.",
                                              ticket_id=s.tickets[-1].ticket_id if s.tickets else None)
    s.state = State.ESCALATED
    s.audit("ESCALATE", {"reason": s.escalation.reason})
    return {"state": s.state, "escalation": s.escalation}


@app.post("/api/v1/sessions/{sid}/end")
def end(sid: str):
    s = _session(sid)
    if s.state != State.ESCALATED:
        s.state = State.CLOSED
    s.audit("CLOSE", {})
    return {"session_id": s.id, "state": s.state, "tickets": s.tickets, "escalation": s.escalation,
            "summary": [t["text"] for t in s.turns if t["speaker"] == "customer"]}


@app.get("/api/v1/sessions/{sid}")
def get_session(sid: str):
    """Full transcript + audit trace (for the ops dashboard)."""
    s = _session(sid)
    return {"session_id": s.id, "state": s.state, "verified": s.verified,
            "customer_id": s.customer_id if s.verified else None, "turns": s.turns,
            "tickets": s.tickets, "escalation": s.escalation, "trace": s.trace}


@app.get("/api/v1/sessions")
def list_sessions():
    return [{"session_id": s.id, "state": s.state, "customer_id": s.customer_id if s.verified else None,
             "tickets": [t.ticket_id for t in s.tickets],
             "escalated": s.escalation is not None} for s in SESSIONS.values()]
