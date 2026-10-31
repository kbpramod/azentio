# VaaniDesk AI Backend (Member 2)

AI orchestration + voice + evaluation for the CSM Voice Agent. Banking systems are **SIMULATED** with synthetic data.
Owner: Member 2 (AI orchestration).

## Setup (Windows, VS Code terminal)

```bash
cd ai
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # add ANTHROPIC_API_KEY to use Claude; without it, rules NLU is used
```

Voice (optional, needs ffmpeg): `pip install -r requirements-voice.txt`

## Run

```bash
uvicorn app.main:app --reload --port 8001
```
Open http://localhost:8001/docs to try every endpoint.

## Test

```bash
python -m pytest -q              # deterministic, rules mode
python -m tests.run_eval         # pass/fail table using the NLU mode in .env
```

## Map: task -> file

| Task | File |
|---|---|
| Speech-to-text | `app/stt.py` |
| Multi-intent detection (Claude + rules fallback) | `app/nlu.py` |
| Conversation state machine | `app/state.py` |
| Policy + tool routing | `app/policy.py`, `app/orchestrator.py` |
| Banking API integration (mock or Member B) | `app/tools.py`, `app/mock_bank.py` |
| Grounded responses + guard | `app/responder.py`, `app/orchestrator.py` |
| TTS contract | `app/tts.py` |
| Fallback + human handoff | `app/orchestrator.py` (`_do_unknown`, `_escalate`) |
| Evaluation cases | `tests/eval_cases.json`, `tests/run_eval.py` |

## API for Member A (frontend)

- `POST /api/v1/sessions` -> `{session_id, reply_text}` (greeting)
- `POST /api/v1/sessions/{id}/turn` -> JSON `{"text": "..."}` or multipart `audio=<file>`; returns `TurnResponse`
  (transcript, intents, verified, reply_text, reply_audio_url, sources, tickets, escalation, latency_ms)
- `POST /api/v1/sessions/{id}/escalate`, `POST /api/v1/sessions/{id}/end`
- `GET /api/v1/sessions/{id}` -> transcript + audit trace (dashboard)

If `reply_audio_url` is null, speak `reply_text` with `window.speechSynthesis`.

## Switching to Member B's banking API

Set `BANKING_API_URL=http://localhost:8000` in `.env`. Needed endpoints are listed in `app/tools.py` (`HttpBank`).
