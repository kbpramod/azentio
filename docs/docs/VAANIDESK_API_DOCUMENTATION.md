# VaaniDesk Banking Assistant: Complete API Reference & Developer Guide

**Project Name:** VaaniDesk (Azentio Banking System)  
**System Role:** Member 1 — Senior Backend Engineer  
**Document Version:** 1.0.0  
**Last Updated:** 2026-10-31  
**Default Base URL:** `http://127.0.0.1:8000`  
**API Canonical Prefix:** `/api/v1`  
**Interactive API Documentation:**  
- Swagger UI: `http://127.0.0.1:8000/docs`  
- ReDoc: `http://127.0.0.1:8000/redoc`  
- OpenAPI JSON: `http://127.0.0.1:8000/api/v1/openapi.json`  

---

## 1. Project Overview

### 1.1 What VaaniDesk Does
VaaniDesk is an enterprise-grade, AI-orchestrated voice and digital customer service assistant engineered for banking and financial services institutions. It provides automated self-service for account inquiries, loan application tracking, loan repayment schedules, and automated dispute resolution while enforcing strict banking security controls.

### 1.2 Backend Architecture & Technologies
- **Application Framework:** FastAPI 0.110+ (Python 3.12, ASGI-driven async architecture).
- **Data Persistence:** Dual-driver Async SQLAlchemy 2.0.
  - **Local Prototype:** SQLite with `aiosqlite` (`sqlite+aiosqlite:///./azentio_banking.db`) requiring zero external setup.
  - **Cloud/Production:** Neon Serverless PostgreSQL with `asyncpg` and SSL termination.
- **Data Serialization & Validation:** Pydantic v2 schemas for all request payloads and response envelopes.
- **Authentication & Cryptography:** JWT (JSON Web Tokens) with HS256 signature and `bcrypt` password hashing.
- **Testing & Quality Assurance:** `pytest` and `httpx` async test harness.

### 1.3 Communication Model Between Frontend and Backend
The frontend (React/Vite single-page application) communicates with the backend via standard HTTP REST calls returning structured JSON payloads. All requests involving active customer interactions utilize a server-controlled session lifecycle (`session_id`) rather than client-trusted state.

### 1.4 Team Responsibilities & Boundaries
- **Member 1 (Backend Engineer — This Implementation):** FastAPI core, database entities, synthetic banking seed data, server-side session management, customer identity verification, mock LOS/LMS/CBS banking APIs, CSM ticket creation with atomic idempotency, call history/audit logging, operations dashboard APIs, and the AI pipeline adapter.
- **Member 2 (AI Orchestrator):** Speech-to-Text (STT), natural language intent recognition, dialogue policy machine, and Text-to-Speech (TTS) response generation. Plugs into `app/integrations/ai_pipeline.py`.
- **Member 3 (Frontend Engineer):** Customer web portal, voice assistant interface, customer verification dialogs, and the staff operations dashboard.

---

## 2. Environment and Server Setup

### 2.1 Software Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- Node.js 18+ (for React client)
- Git

### 2.2 Environment Configuration
Create or inspect `azentio/server/.env`:
```ini
PROJECT_NAME="Azentio Banking System"
API_V1_STR="/api/v1"
DEBUG=true
HOST="127.0.0.1"
PORT=8000
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://127.0.0.1:3000","http://127.0.0.1:5173"]

# Leave DATABASE_URL empty or unset for instant local SQLite prototype
DATABASE_URL=""

# JWT Secret Key
SECRET_KEY="azentio-banking-jwt-secret-key-change-in-production-2026"
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

### 2.3 Starting the Backend
```bash
# Navigate to backend directory
cd azentio/server

# Activate Python virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Seed synthetic banking data (idempotent, safe to repeat)
python -m app.db.seed

# Run development server
python run.py
# Alternatively:
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 3. Complete API Endpoint Reference & Input/Output Specs

### 3.1 System Health Probes

#### `GET /health` (Canonical Service Health)
- **Purpose:** Infrastructure liveness probe.
- **Authentication:** None.
- **INPUT:** None.
- **OUTPUT:**
  ```json
  {
    "status": "ok",
    "service": "vaanidesk-backend"
  }
  ```
- **Status:** Implemented and Tested.

#### `GET /api/v1/health` (Extended Diagnostic Health)
- **Purpose:** Returns service runtime metadata and timestamp.
- **Authentication:** None.
- **INPUT:** None.
- **OUTPUT:**
  ```json
  {
    "status": "ok",
    "app_name": "Azentio Banking System",
    "version": "1.0.0",
    "environment": "development",
    "timestamp": "2026-10-31T12:00:00Z"
  }
  ```
- **Status:** Implemented and Tested.

---

### 3.2 Customer Voice & Chat Session Management

#### `POST /api/v1/sessions` (Create New Session)
- **Purpose:** Initializes a new voice or digital assistant session and creates an associated call audit record.
- **Authentication:** None.

**INPUT**
- **Headers:** `Content-Type: application/json`
- **Request Body (Optional):**
  ```json
  {
    "customer_id": "C1023",
    "channel": "voice"
  }
  ```
  *(If customer_id is omitted, session begins as unassigned).*

**OUTPUT**
- **HTTP Status:** `201 Created`
- **Success Response:**
  ```json
  {
    "session_id": "SES-3f92a10b",
    "call_id": "CALL-7e81b29c",
    "customer_id": "C1023",
    "current_state": "UNVERIFIED",
    "verified": false,
    "failed_verification_attempts": 0,
    "locked": false,
    "created_at": "2026-10-31T12:01:00Z"
  }
  ```
- **Frontend Action:** Store `session_id` and `call_id` in application state to pass with subsequent conversation turns.
- **Status:** Implemented and Tested.

---

#### `POST /api/v1/sessions/{session_id}/verify` (Customer Identity Verification)
- **Purpose:** Verifies customer identity using DOB against synthetic records. Enforces a 3-attempt brute-force lockout rule entirely on the server.
- **Authentication:** Valid active session.

**INPUT**
- **Path Parameter:** `session_id` (string, required)
- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "customer_id": "C1023",
    "dob": "1995-03-12"
  }
  ```
- **Validation Rules:** `customer_id` must be non-empty; `dob` must match `YYYY-MM-DD`.

**OUTPUT**
- **HTTP Status (Success):** `200 OK`
- **Success Response:**
  ```json
  {
    "session_id": "SES-3f92a10b",
    "verified": true,
    "customer_id": "C1023",
    "customer_name": "Alex Mercer",
    "current_state": "VERIFIED",
    "message": "Customer identity verified successfully."
  }
  ```
- **HTTP Status (Verification Mismatch):** `401 Unauthorized`
  ```json
  {
    "error": {
      "code": "AUTH_MISMATCH",
      "message": "Verification failed. Date of birth does not match. 2 attempts remaining.",
      "retryable": true
    }
  }
  ```
- **HTTP Status (Session Lockout):** `403 Forbidden`
  ```json
  {
    "error": {
      "code": "LOCKED",
      "message": "Session locked due to 3 failed verification attempts. Human supervisor handoff required.",
      "retryable": false
    }
  }
  ```
- **Frontend Action:** On `verified: true`, transition UI to authorized banking mode. On `LOCKED`, disable verification inputs and prompt user to escalate to a human agent.
- **Status:** Implemented and Tested.

---

#### `POST /api/v1/sessions/{session_id}/turn` (Submit Conversation Turn)
- **Purpose:** Processes a voice transcript or text query through Member 2's AI integration pipeline, records the conversation turn, and logs audit events.
- **Authentication:** Valid session. Sensitive banking intents are gated behind `session.verified is True`.

**INPUT**
- **Path Parameter:** `session_id` (string, required)
- **Request Body:**
  ```json
  {
    "text": "What is the status of my loan application?",
    "input_type": "voice_transcript"
  }
  ```

**OUTPUT**
- **HTTP Status:** `200 OK`
- **Success Response:**
  ```json
  {
    "turn_id": "TURN-1029",
    "session_id": "SES-3f92a10b",
    "call_id": "CALL-7e81b29c",
    "turn_number": 1,
    "reply_text": "Your Personal Loan application APP-77 is currently in Document Verification. A salary slip document is pending submission.",
    "detected_intents": ["los_status_query"],
    "state": "VERIFIED",
    "verified": true,
    "tickets": [],
    "escalation": null
  }
  ```
- **Frontend Action:** Play synthesized audio or display `reply_text` in chat UI.
- **Status:** Implemented and Tested.

---

#### `POST /api/v1/sessions/{session_id}/escalate` (Escalate to Human Agent)
- **Purpose:** Escalates the session to a human representative, generates a ticket, and flags the call record.
- **Authentication:** Valid session.

**INPUT**
- **Path Parameter:** `session_id` (string, required)
- **Request Body:**
  ```json
  {
    "reason": "Customer dissatisfied with automated response regarding overdue fee",
    "category": "complaint",
    "priority": "HIGH"
  }
  ```

**OUTPUT**
- **HTTP Status:** `200 OK`
- **Success Response:**
  ```json
  {
    "session_id": "SES-3f92a10b",
    "call_id": "CALL-7e81b29c",
    "escalated": true,
    "escalation_id": "ESC-5012",
    "ticket_id": "SR-9011",
    "message": "Call successfully transferred to human agent queue."
  }
  ```
- **Frontend Action:** Display transfer notice and provide `ticket_id` reference to customer.
- **Status:** Implemented and Tested.

---

#### `POST /api/v1/sessions/{session_id}/end` (End Call Session)
- **Purpose:** Closes session and records final call duration and outcome.
- **Authentication:** Valid session.

**INPUT**
- **Path Parameter:** `session_id` (string, required)
- **Request Body (Optional):**
  ```json
  {
    "reason": "Customer completed transaction inquiries"
  }
  ```

**OUTPUT**
- **HTTP Status:** `200 OK`
- **Success Response:**
  ```json
  {
    "session_id": "SES-3f92a10b",
    "call_id": "CALL-7e81b29c",
    "status": "ENDED",
    "message": "Session terminated successfully."
  }
  ```
- **Status:** Implemented and Tested.

---

### 3.3 Mock Banking Services (LOS, LMS, CBS)

#### `GET /api/v1/mock/los/applications` (Loan Origination System)
- **Purpose:** Fetches loan applications and pending document requirements for an authenticated customer.
- **Authentication:** Verified session (passed via `X-Session-ID` header or `session_id` query parameter).

**INPUT**
- **Query Parameter:** `customer_id=C1023` (required)
- **Headers:** `X-Session-ID: SES-3f92a10b`

**OUTPUT**
- **HTTP Status:** `200 OK`
- **Success Response:**
  ```json
  {
    "customer_id": "C1023",
    "applications": [
      {
        "application_id": "APP-77",
        "product_type": "personal",
        "requested_amount": 300000.0,
        "application_status": "DOC_VERIFICATION",
        "pending_documents": ["salary_slip"],
        "created_at": "2026-10-15T09:30:00Z"
      }
    ],
    "source": "LOS-SIMULATED"
  }
  ```
- **Error Response (`403 Forbidden` if unverified or wrong customer):**
  ```json
  {
    "error": {
      "code": "NOT_VERIFIED",
      "message": "Customer verification is required before accessing loan applications.",
      "retryable": false
    }
  }
  ```
- **Status:** Implemented and Tested.

---

#### `GET /api/v1/mock/lms/loans/{loan_id}` (Loan Details)
- **Purpose:** Retrieves loan balance, monthly EMI, next payment due date, and overdue amounts.
- **Authentication:** Verified session for loan owner.

**INPUT**
- **Path Parameter:** `loan_id` (e.g. `LN-9012`)
- **Headers:** `X-Session-ID: SES-3f92a10b`

**OUTPUT**
- **HTTP Status:** `200 OK`
- **Success Response:**
  ```json
  {
    "loan_id": "LN-9012",
    "customer_id": "C1023",
    "application_id": "APP-70",
    "product_type": "home_loan",
    "outstanding_amount": 2450000.0,
    "emi_amount": 28500.0,
    "next_due_date": "2026-11-05",
    "overdue_amount": 0.0,
    "loan_status": "ACTIVE",
    "source": "LMS-SIMULATED"
  }
  ```
- **Status:** Implemented and Tested.

---

#### `GET /api/v1/mock/lms/loans/{loan_id}/schedule` (Repayment Schedule)
- **Purpose:** Retrieves installment breakdown and payment status.
- **Authentication:** Verified session for loan owner.

**INPUT**
- **Path Parameter:** `loan_id` (e.g. `LN-9012`)
- **Headers:** `X-Session-ID: SES-3f92a10b`

**OUTPUT**
- **HTTP Status:** `200 OK`
- **Success Response:**
  ```json
  {
    "loan_id": "LN-9012",
    "schedule": [
      {
        "schedule_id": "SCH-101",
        "installment_number": 1,
        "due_date": "2026-10-05",
        "amount": 28500.0,
        "payment_status": "PAID"
      },
      {
        "schedule_id": "SCH-102",
        "installment_number": 2,
        "due_date": "2026-11-05",
        "amount": 28500.0,
        "payment_status": "PENDING"
      }
    ],
    "source": "LMS-SIMULATED"
  }
  ```
- **Status:** Implemented and Tested.

---

#### `GET /api/v1/mock/cbs/accounts/{account_id}` (Core Banking Account)
- **Purpose:** Returns account balances with sensitive account number masking.
- **Authentication:** Verified session for account owner.

**INPUT**
- **Path Parameter:** `account_id` (e.g. `ACC-1001`)
- **Headers:** `X-Session-ID: SES-3f92a10b`

**OUTPUT**
- **HTTP Status:** `200 OK`
- **Success Response:**
  ```json
  {
    "account_id": "ACC-1001",
    "customer_id": "C1023",
    "masked_account": "****8821",
    "account_type": "savings",
    "balance": 145000.5,
    "currency": "INR",
    "account_status": "ACTIVE",
    "source": "CBS-SIMULATED"
  }
  ```
- **Status:** Implemented and Tested.

---

#### `GET /api/v1/mock/cbs/transactions/{transaction_id}` (CBS Transaction Details)
- **Purpose:** Returns synthetic transaction information.
- **Authentication:** Verified session.

**INPUT**
- **Path Parameter:** `transaction_id` (e.g. `TX-5501`)
- **Headers:** `X-Session-ID: SES-3f92a10b`

**OUTPUT**
- **HTTP Status:** `200 OK`
- **Success Response:**
  ```json
  {
    "transaction_id": "TX-5501",
    "account_id": "ACC-1001",
    "amount": 4500.0,
    "transaction_type": "DEBIT",
    "transaction_status": "SUCCESS",
    "transaction_date": "2026-10-29T14:22:10Z",
    "merchant_description": "Supermarket Retail Hub",
    "source": "CBS-SIMULATED"
  }
  ```
- **Status:** Implemented and Tested.

---

### 3.4 Customer Service Management (CSM Tickets)

#### `POST /api/v1/mock/csm/tickets` (Create Ticket with Idempotency)
- **Purpose:** Creates a support ticket with database-level uniqueness enforcement on `idempotency_key`. Repeating a request with the same idempotency key returns the original ticket without creating duplicates.
- **Authentication:** Verified session.

**INPUT**
- **Headers:** `Content-Type: application/json`, `X-Session-ID: SES-3f92a10b`
- **Request Body:**
  ```json
  {
    "customer_id": "C1023",
    "type": "service_request",
    "category": "repayment_schedule",
    "summary": "Customer requested loan repayment schedule PDF via email",
    "priority": "NORMAL",
    "call_id": "CALL-7e81b29c",
    "idempotency_key": "SES-3f92a10b-turn2"
  }
  ```

**OUTPUT**
- **HTTP Status:** `201 Created` (or `200 OK` if key already processed)
- **Success Response:**
  ```json
  {
    "ticket_id": "SR-4471",
    "status": "OPEN",
    "customer_id": "C1023",
    "type": "service_request",
    "category": "repayment_schedule",
    "summary": "Customer requested loan repayment schedule PDF via email",
    "priority": "NORMAL",
    "call_id": "CALL-7e81b29c",
    "idempotency_key": "SES-3f92a10b-turn2",
    "created_at": "2026-10-31T12:05:00Z"
  }
  ```
- **Status:** Implemented and Tested.

---

#### `GET /api/v1/mock/csm/tickets/{ticket_id}` (Retrieve Ticket)
- **Purpose:** Fetches ticket details by ticket reference ID.
- **Authentication:** Verified session for customer or staff role.

**OUTPUT**
- **HTTP Status:** `200 OK`
- **Success Response:**
  ```json
  {
    "ticket_id": "SR-4471",
    "customer_id": "C1023",
    "type": "service_request",
    "category": "repayment_schedule",
    "summary": "Customer requested loan repayment schedule PDF via email",
    "priority": "NORMAL",
    "status": "OPEN",
    "created_at": "2026-10-31T12:05:00Z"
  }
  ```
- **Status:** Implemented and Tested.

---

### 3.5 Operations Dashboard APIs

#### `GET /api/v1/ops/calls` (List Calls)
- **Purpose:** Returns paginated call records for supervisor review.
- **Query Parameters:**
  - `limit` (integer, default 20)
  - `offset` (integer, default 0)
  - `customer_id` (string, optional)
- **OUTPUT (`200 OK`):**
  ```json
  {
    "total": 12,
    "calls": [
      {
        "call_id": "CALL-7e81b29c",
        "session_id": "SES-3f92a10b",
        "customer_id": "C1023",
        "started_at": "2026-10-31T12:01:00Z",
        "ended_at": "2026-10-31T12:08:15Z",
        "outcome": "RESOLVED",
        "escalation_status": "NONE"
      }
    ]
  }
  ```
- **Status:** Implemented and Tested.

#### `GET /api/v1/ops/calls/{call_id}` (Call Deep Dive)
- **Purpose:** Full audit view of a call, including all conversation turns and redacted audit events.
- **OUTPUT (`200 OK`):**
  ```json
  {
    "call_id": "CALL-7e81b29c",
    "session_id": "SES-3f92a10b",
    "customer_id": "C1023",
    "started_at": "2026-10-31T12:01:00Z",
    "ended_at": "2026-10-31T12:08:15Z",
    "outcome": "RESOLVED",
    "escalation_status": "NONE",
    "turns": [
      {
        "turn_id": "TURN-1029",
        "turn_number": 1,
        "transcript": "What is the status of my loan application?",
        "reply_text": "Your Personal Loan application APP-77 is currently in Document Verification.",
        "detected_intents": ["los_status_query"],
        "created_at": "2026-10-31T12:01:30Z"
      }
    ],
    "tickets": ["SR-4471"],
    "audit_events": [
      {
        "event_type": "SESSION_CREATED",
        "event_status": "SUCCESS",
        "created_at": "2026-10-31T12:01:00Z"
      },
      {
        "event_type": "VERIFICATION_SUCCESS",
        "event_status": "SUCCESS",
        "created_at": "2026-10-31T12:01:25Z"
      }
    ]
  }
  ```
- **Status:** Implemented and Tested.

#### `GET /api/v1/ops/tickets` (List Tickets)
- **Query Parameters:** `status` (OPEN/CLOSED), `priority` (HIGH/NORMAL), `category`.
- **OUTPUT (`200 OK`):**
  ```json
  {
    "total": 3,
    "tickets": [
      {
        "ticket_id": "SR-4471",
        "customer_id": "C1023",
        "category": "repayment_schedule",
        "priority": "NORMAL",
        "status": "OPEN",
        "created_at": "2026-10-31T12:05:00Z"
      }
    ]
  }
  ```
- **Status:** Implemented and Tested.

#### `GET /api/v1/ops/escalations` (List Active Escalations)
- **OUTPUT (`200 OK`):**
  ```json
  {
    "total": 1,
    "escalations": [
      {
        "escalation_id": "ESC-5012",
        "call_id": "CALL-7e81b29c",
        "session_id": "SES-3f92a10b",
        "customer_id": "C1023",
        "reason": "Customer requested human supervisor",
        "ticket_id": "SR-9011",
        "status": "PENDING_AGENT",
        "created_at": "2026-10-31T12:06:00Z"
      }
    ]
  }
  ```
- **Status:** Implemented and Tested.

---

## 4. API Endpoint Summary Table

| Method | Endpoint | Purpose | Authentication | Request Input | Response Output | Status |
|---|---|---|---|---|---|---|
| `GET` | `/health` | Canary health probe | None | None | `{status: "ok", service: "vaanidesk-backend"}` | Tested |
| `GET` | `/api/v1/health` | Extended service health | None | None | HealthResponse metadata | Tested |
| `POST` | `/api/v1/sessions` | Create assistant session | None | `{customer_id?, channel?}` | Session details & call_id | Tested |
| `POST` | `/api/v1/sessions/{id}/verify` | Verify customer DOB | Active session | `{customer_id, dob}` | Verification status & lockout | Tested |
| `POST` | `/api/v1/sessions/{id}/turn` | Process conversation turn | Active session | `{text, input_type?}` | AI reply, intents, turn_id | Tested |
| `POST` | `/api/v1/sessions/{id}/escalate` | Escalate to human supervisor | Active session | `{reason, category?, priority?}` | Escalation record & ticket | Tested |
| `POST` | `/api/v1/sessions/{id}/end` | Close call & session | Active session | `{reason?}` | Session ended confirmation | Tested |
| `GET` | `/api/v1/mock/los/applications` | Loan origination applications | Verified session | Query: `?customer_id=...` | Applications & pending docs | Tested |
| `GET` | `/api/v1/mock/lms/loans/{id}` | Loan details & balance | Verified session | Path `loan_id` | Outstanding, EMI, status | Tested |
| `GET` | `/api/v1/mock/lms/loans/{id}/schedule` | Loan repayment schedule | Verified session | Path `loan_id` | Installment breakdown | Tested |
| `GET` | `/api/v1/mock/cbs/accounts/{id}` | Core banking account balance | Verified session | Path `account_id` | Masked account & balance | Tested |
| `GET` | `/api/v1/mock/cbs/transactions/{id}` | CBS transaction details | Verified session | Path `transaction_id` | Transaction status & merchant | Tested |
| `POST` | `/api/v1/mock/csm/tickets` | Create ticket (idempotent) | Verified session | Ticket body + idempotency_key | Ticket details | Tested |
| `GET` | `/api/v1/mock/csm/tickets/{id}` | Retrieve ticket status | Verified session | Path `ticket_id` | Ticket record | Tested |
| `GET` | `/api/v1/ops/calls` | Operations call listing | Staff / Local | Query pagination | Call list with outcomes | Tested |
| `GET` | `/api/v1/ops/calls/{id}` | Call conversation & audit trace | Staff / Local | Path `call_id` | Full turns & sanitized trace | Tested |
| `GET` | `/api/v1/ops/tickets` | Operations ticket queue | Staff / Local | Filter params | Filtered tickets | Tested |
| `GET` | `/api/v1/ops/escalations` | Operations escalation queue | Staff / Local | Filter params | Active escalation list | Tested |
| `POST` | `/api/v1/auth/register` | Customer web portal register | None | Email, password, name | JWT token + User | Preserved |
| `POST` | `/api/v1/auth/login` | Customer web portal login | None | Email, password | JWT token + User | Preserved |
| `POST` | `/api/v1/auth/logout` | Customer web portal logout | Bearer token | None | Success message | Preserved |
| `GET` | `/api/v1/auth/me` | Customer portal profile | Bearer token | None | Current user object | Preserved |
| `GET` | `/api/v1/banking/account` | Customer portal account | Bearer token | None | User account | Preserved |
| `GET` | `/api/v1/banking/transactions` | Customer portal transactions | Bearer token | None | Transaction list | Preserved |
| `POST` | `/api/v1/banking/transfer` | Customer fund transfer | Bearer token | Recipient, amount, note | Outflow transaction | Preserved |
| `POST` | `/api/v1/banking/deposit` | Customer deposit | Bearer token | Amount, note | Inflow transaction | Preserved |
| `POST` | `/api/v1/agent/chat` | Portal AI assistant | Bearer token | `{message}` | Reply & credit deduction | Preserved |

---

## 5. Frontend Integration Guide

### 5.1 Base Configuration
In React/Vite, configure the API client base URL:
```javascript
// src/services/vaaniApi.js
const API_BASE = 'http://127.0.0.1:8000/api/v1';

export async function request(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const error = new Error(data?.error?.message || data?.detail || 'Request failed');
    error.code = data?.error?.code || 'UNKNOWN_ERROR';
    error.status = res.status;
    throw error;
  }
  return data;
}
```

### 5.2 Complete Voice Assistant Session Lifecycle

```javascript
// Step 1: Start Session
export async function startAssistantSession(channel = 'web_voice') {
  return request('/sessions', {
    method: 'POST',
    body: JSON.stringify({ channel })
  });
}

// Step 2: Verify Identity
export async function verifyCustomer(sessionId, customerId, dob) {
  return request(`/sessions/${sessionId}/verify`, {
    method: 'POST',
    body: JSON.stringify({ customer_id: customerId, dob })
  });
}

// Step 3: Send Transcript Turn
export async function sendTurn(sessionId, userSpeechText) {
  return request(`/sessions/${sessionId}/turn`, {
    method: 'POST',
    body: JSON.stringify({
      text: userSpeechText,
      input_type: 'voice_transcript'
    })
  });
}

// Step 4: Escalate If Needed
export async function escalateSession(sessionId, reason) {
  return request(`/sessions/${sessionId}/escalate`, {
    method: 'POST',
    body: JSON.stringify({ reason })
  });
}

// Step 5: End Session
export async function endSession(sessionId) {
  return request(`/sessions/${sessionId}/end`, {
    method: 'POST'
  });
}
```

---

## 6. Error Handling Standard

The VaaniDesk backend uses explicit, structured HTTP error bodies:

```json
{
  "error": {
    "code": "AUTH_MISMATCH",
    "message": "Date of birth does not match customer record. 2 attempts remaining.",
    "retryable": true
  }
}
```

### Supported Error Codes

| Code | HTTP Status | Meaning | Retryable? |
|---|---|---|---|
| `NOT_FOUND` | 404 | Session, customer, loan, or ticket does not exist | No |
| `NOT_VERIFIED` | 403 | Sensitive banking query attempted prior to verification | Yes (after verify) |
| `AUTH_MISMATCH` | 401 | Verification credentials (DOB) incorrect | Yes (< 3 attempts) |
| `LOCKED` | 403 | Session locked due to 3 consecutive failures | No (must escalate) |
| `CONFLICT` | 409 | Duplicate entity or conflicting idempotency key | No |
| `BAD_REQUEST` | 400 | Missing required fields or schema violation | No |
| `INTERNAL_ERROR`| 500 | Unexpected server or upstream error | Yes |

---

## 7. Data and Security Safeguards

1. **Synthetic Data Exclusively:** All customer identities (`C1023`, `C1024`, etc.), bank accounts (`ACC-1001`), and loan numbers (`LN-9012`) are fictional. No production data is ever loaded.
2. **PII and Secret Redaction:** Audit events and conversation logs automatically mask complete account numbers (`****8821`), strip date of birth from event traces, and never log passwords or JWT tokens.
3. **Server-Side Verification Authority:** Client requests cannot bypass identity verification by passing flags such as `verified=true`. Verification state is owned entirely by the server database.
4. **Brute-Force Lockout:** Attempt counters are maintained transactionally in the database. When `failed_verification_attempts >= 3`, the session is permanently locked.
