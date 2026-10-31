# VaaniDesk (Azentio Banking System) — Backend Server

FastAPI backend server for **VaaniDesk**, an AI-powered voice and digital customer service banking assistant.

---

## 🏛️ System Architecture

```
azentio/server/
├── app/
│   ├── main.py                     # Canonical FastAPI factory, lifespan, CORS, routes
│   ├── api/
│   │   └── v1/
│   │       ├── api.py              # Central API router aggregator
│   │       └── endpoints/
│   │           ├── health.py       # Diagnostic health check
│   │           ├── sessions.py     # Voice & chat session lifecycle, verification, turns, escalation
│   │           ├── mock_banking.py # Mock LOS (origination), LMS (servicing), CBS (core banking)
│   │           ├── csm.py          # Customer service tickets with atomic idempotency
│   │           ├── ops.py          # Operations dashboard (calls, tickets, escalations)
│   │           ├── auth.py         # Customer portal authentication (JWT + bcrypt)
│   │           ├── banking.py      # Customer portal account & transfer operations
│   │           └── agent.py        # Customer portal rule-based & AI credit agent
│   ├── core/
│   │   ├── config.py               # Pydantic Settings (SQLite / Neon PostgreSQL dual-mode)
│   │   ├── exceptions.py           # Structured VaaniDesk error envelope handler
│   │   └── security.py             # JWT token handling & password hashing
│   ├── db/
│   │   ├── session.py              # Async SQLAlchemy engine (aiosqlite & asyncpg)
│   │   └── seed.py                 # Repeatable synthetic banking dataset seeder
│   ├── models/
│   │   ├── user.py                 # Customer portal web user model
│   │   ├── transaction.py          # Customer portal transaction model
│   │   └── vaani_models.py         # VaaniDesk core banking, session, call, turn, ticket models
│   ├── schemas/
│   │   ├── auth.py                 # Auth schemas
│   │   ├── common.py               # Health & generic schemas
│   │   └── vaani_schemas.py        # Session, LOS, LMS, CBS, CSM, and Ops schemas
│   ├── services/
│   │   ├── session_service.py      # Session state machine & call tracking
│   │   ├── verification_service.py # DOB customer verification & 3-attempt lockout
│   │   ├── banking_service.py      # LOS, LMS, CBS data layer with session auth
│   │   ├── ticket_service.py       # CSM ticket persistence with atomic deduplication
│   │   ├── ops_service.py          # Operations reporting & call trace retrieval
│   │   └── audit_service.py        # Sensitive PII redaction and audit logging
│   └── integrations/
│       └── ai_pipeline.py          # Member 2 AI orchestration adapter & fallback
├── tests/
│   ├── conftest.py                 # Pytest async HTTP client fixtures
│   ├── test_api.py                 # Base API & item tests
│   ├── test_banking_auth.py        # Portal auth & banking flow tests
│   └── test_vaani_backend.py       # Complete VaaniDesk test suite (20/20 passing)
├── .env                            # Active environment configuration
├── .env.example                    # Environment template
├── requirements.txt                # Pinned production and test dependencies
└── run.py                          # Server launcher
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- Virtual environment in `.venv/`

### 2. Activate Virtual Environment
```powershell
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
```

### 3. Seed Repeatable Synthetic Banking Data
```powershell
python -m app.db.seed
```
*Seeds customers (`C1023`, `C1024`, `C1099`), loan applications, active loans, EMI repayment schedules, accounts, and transactions into local SQLite database (`azentio_banking.db`). Safe to run repeatedly.*

### 4. Run the Development Server
```powershell
python run.py
# Or with uvicorn:
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Base URL:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Canonical Health Probe:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🧪 Running Automated Tests

```powershell
pytest tests/ -v
```
All 20 test cases cover:
- Canonical `/health` probe
- Session creation, lockout after 3 failed attempts, session termination
- Customer verification via DOB
- Mock LOS loan applications & document requirements
- Mock LMS loan balance & repayment schedules
- Mock CBS masked accounts & transactions
- CSM ticket creation & atomic idempotency enforcement
- AI conversation turns & state machine gating
- Session escalation to human agents
- Operations dashboard call history & audit traces

---

## 📚 Documentation Reference

- **Complete API Reference (Markdown):** `docs/VAANIDESK_API_DOCUMENTATION.md`
- **Complete API Reference (PDF):** `docs/VAANIDESK_API_DOCUMENTATION.pdf`
- **Formal API Contract:** `docs/API_CONTRACT.md`
- **Backend Architecture Audit:** `docs/BACKEND_AUDIT.md`
- **Frontend Handoff Guide:** `docs/FRONTEND_API_HANDOFF.md`
