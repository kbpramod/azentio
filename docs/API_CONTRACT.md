# VaaniDesk API Contract Specification

**Project:** VaaniDesk — AI-Powered Voice Customer Service Assistant for Banking  
**Document Version:** 1.0.0  
**Date:** 2026-10-31  
**Owner:** Member 1 — Senior Backend Engineer  
**Consumers:** Member 2 (AI Orchestration Backend), Member 3 (React Frontend)  

---

## 1. Overview & Architectural Principles

1. **Protocol & Formats:** All endpoints communicate over HTTP/HTTPS using standard JSON payloads (`Content-Type: application/json`).
2. **Canonical Prefix:** All core API routes reside under `/api/v1` except the global `/health` probe and `/docs` / `/redoc` OpenAPI interfaces.
3. **Session & Security Model:**
   - Client calls begin by creating a session (`POST /api/v1/sessions`).
   - Customer verification is performed server-side via `POST /api/v1/sessions/{session_id}/verify` validating `customer_id` and `dob`.
   - The server maintains verification attempt counters. After three (3) consecutive failures, the session is permanently locked (`LOCKED`) and sensitive operations are blocked.
   - Frontend-supplied `verified: true` flags are never trusted.
   - Banking resources (LOS, LMS, CBS, CSM) require the session to be verified and enforce that the customer ID matches the session owner.
4. **Idempotency:**
   - Ticket creation (`POST /api/v1/mock/csm/tickets`) requires an `idempotency_key`. Repeating a request with the same idempotency key returns the previously created ticket without duplicate database records.
5. **Standardized Error Envelope:**
   All errors follow the uniform structure:
   ```json
   {
     "error": {
       "code": "AUTH_MISMATCH",
       "message": "Customer verification details do not match.",
       "retryable": true
     }
   }
   ```

---

## 2. API Endpoint Matrix

| Method | Endpoint | Description | Auth / Session | Request Body | Response Output | Ownership / Status |
|---|---|---|---|---|---|---|
| `GET` | `/health` | Service health check | None | None | `{status: "ok", service: "vaanidesk-backend"}` | Member 1 (Canonical) |
| `GET` | `/api/v1/health` | Service health & timestamp | None | None | `HealthResponse` | Member 1 (Existing) |
| `POST` | `/api/v1/sessions` | Create voice/agent session | None | `{customer_id?: string, channel?: string}` | Session object with `session_id`, `state="UNVERIFIED"`, `call_id` | Member 1 |
| `POST` | `/api/v1/sessions/{session_id}/verify` | Verify customer DOB & ID | Valid session | `{customer_id: string, dob: string}` | Session verification outcome (`verified: true`, attempts, customer) | Member 1 |
| `POST` | `/api/v1/sessions/{session_id}/turn` | Process conversation turn | Valid session | `{text: string, input_type?: string}` | AI response object with `reply_text`, `intents`, `state`, `turn_id` | Member 1 (Adapter) / Member 2 (AI) |
| `POST` | `/api/v1/sessions/{session_id}/escalate` | Escalate call to human agent | Valid session | `{reason: string, category?: string, priority?: string}` | Escalation reference & ticket object | Member 1 |
| `POST` | `/api/v1/sessions/{session_id}/end` | End session & call | Valid session | `{reason?: string}` | Session closure confirmation | Member 1 |
| `GET` | `/api/v1/mock/los/applications` | List loan applications | Verified session | Query: `?customer_id=C1023` | Application list with statuses and pending documents | Member 1 |
| `GET` | `/api/v1/mock/lms/loans/{loan_id}` | Get loan details | Verified session | Header/Query: `session_id` | Loan details (outstanding, EMI, due date, status) | Member 1 |
| `GET` | `/api/v1/mock/lms/loans/{loan_id}/schedule` | Get loan repayment schedule | Verified session | Header/Query: `session_id` | List of EMI installments with payment status | Member 1 |
| `GET` | `/api/v1/mock/cbs/accounts/{account_id}` | Get CBS account info | Verified session | Header/Query: `session_id` | Masked account details, balance, status | Member 1 |
| `GET` | `/api/v1/mock/cbs/transactions/{tx_id}` | Get CBS transaction info | Verified session | Header/Query: `session_id` | Transaction status and details | Member 1 |
| `POST` | `/api/v1/mock/csm/tickets` | Create service ticket | Verified session | Ticket payload + `idempotency_key` | Created/Existing ticket reference & status | Member 1 |
| `GET` | `/api/v1/mock/csm/tickets/{ticket_id}` | Get ticket details | Verified session | Header/Query: `session_id` | Ticket status and metadata | Member 1 |
| `GET` | `/api/v1/ops/calls` | List call history | Admin / Ops | Query: `limit`, `offset`, `customer_id` | List of calls with summary metrics | Member 1 |
| `GET` | `/api/v1/ops/calls/{call_id}` | Get call detail & trace | Admin / Ops | None | Full call record, conversation turns, audit trace | Member 1 |
| `GET` | `/api/v1/ops/tickets` | List ops tickets | Admin / Ops | Query: `status`, `priority`, `category` | Filtered ticket collection | Member 1 |
| `GET` | `/api/v1/ops/escalations` | List open escalations | Admin / Ops | Query: `status` | Escalation list with call & ticket links | Member 1 |
| `POST` | `/api/v1/auth/register` | Register portal customer | None | Email, password, full name, deposit | JWT access token + User info | Preserved (Portal) |
| `POST` | `/api/v1/auth/login` | Login portal customer | None | Email, password | JWT access token + User info | Preserved (Portal) |
| `POST` | `/api/v1/auth/logout` | Logout portal customer | Bearer token | None | Success message | Preserved (Portal) |
| `GET` | `/api/v1/auth/me` | Current portal customer | Bearer token | None | User profile | Preserved (Portal) |
| `GET` | `/api/v1/banking/account` | Current portal account | Bearer token | None | User account summary | Preserved (Portal) |
| `GET` | `/api/v1/banking/transactions` | Portal transactions | Bearer token | None | Transaction records | Preserved (Portal) |
| `POST` | `/api/v1/banking/transfer` | Portal fund transfer | Bearer token | Recipient account, amount, note | Transaction record | Preserved (Portal) |
| `POST` | `/api/v1/banking/deposit` | Portal fund deposit | Bearer token | Amount, note | Transaction record | Preserved (Portal) |
| `POST` | `/api/v1/agent/chat` | Portal AI assistant | Bearer token | `{message: string}` | AI reply & credit balance | Preserved (Portal) |

---

## 3. Detailed Request and Response Schemas

### 3.1 Session Creation
- **Endpoint:** `POST /api/v1/sessions`
- **Request Body (Optional):**
  ```json
  {
    "customer_id": "C1023",
    "channel": "voice"
  }
  ```
- **Success Response (`201 Created`):**
  ```json
  {
    "session_id": "SES-8a4b2c1d",
    "call_id": "CALL-9f1e8a2b",
    "current_state": "UNVERIFIED",
    "verified": false,
    "failed_verification_attempts": 0,
    "locked": false,
    "created_at": "2026-10-31T12:00:00Z"
  }
  ```

### 3.2 Customer Identity Verification
- **Endpoint:** `POST /api/v1/sessions/{session_id}/verify`
- **Request Body:**
  ```json
  {
    "customer_id": "C1023",
    "dob": "1995-03-12"
  }
  ```
- **Success Response (`200 OK`):**
  ```json
  {
    "session_id": "SES-8a4b2c1d",
    "verified": true,
    "customer_id": "C1023",
    "customer_name": "Alex Mercer",
    "current_state": "VERIFIED",
    "message": "Customer identity verified successfully."
  }
  ```
- **Failure Response (`401 Unauthorized` - Attempt 1 or 2):**
  ```json
  {
    "error": {
      "code": "AUTH_MISMATCH",
      "message": "Date of birth does not match customer record. 2 attempts remaining.",
      "retryable": true
    }
  }
  ```
- **Lockout Response (`403 Forbidden` - Attempt 3):**
  ```json
  {
    "error": {
      "code": "LOCKED",
      "message": "Session locked due to 3 failed verification attempts. Please contact a human agent.",
      "retryable": false
    }
  }
  ```

### 3.3 Conversation Turn
- **Endpoint:** `POST /api/v1/sessions/{session_id}/turn`
- **Request Body:**
  ```json
  {
    "text": "What is the status of my loan application?",
    "input_type": "voice_transcript"
  }
  ```
- **Success Response (`200 OK`):**
  ```json
  {
    "turn_id": "TURN-4421",
    "session_id": "SES-8a4b2c1d",
    "call_id": "CALL-9f1e8a2b",
    "turn_number": 1,
    "reply_text": "Your Personal Loan application APP-77 is currently in Document Verification. A salary slip document is pending submission.",
    "detected_intents": ["los_status_query"],
    "state": "VERIFIED",
    "verified": true,
    "tickets": [],
    "escalation": null
  }
  ```

### 3.4 Mock LOS Applications
- **Endpoint:** `GET /api/v1/mock/los/applications?customer_id=C1023`
- **Headers:** `X-Session-ID: SES-8a4b2c1d` (or query param `session_id=SES-8a4b2c1d`)
- **Success Response (`200 OK`):**
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

### 3.5 Mock LMS Loan Details & Repayment Schedule
- **Endpoint:** `GET /api/v1/mock/lms/loans/{loan_id}`
- **Headers:** `X-Session-ID: SES-8a4b2c1d`
- **Success Response (`200 OK`):**
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
- **Endpoint:** `GET /api/v1/mock/lms/loans/{loan_id}/schedule`
- **Success Response (`200 OK`):**
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

### 3.6 CSM Ticket Creation & Retrieval
- **Endpoint:** `POST /api/v1/mock/csm/tickets`
- **Headers:** `X-Session-ID: SES-8a4b2c1d`
- **Request Body:**
  ```json
  {
    "customer_id": "C1023",
    "type": "service_request",
    "category": "repayment_schedule",
    "summary": "Customer requested repayment schedule statement via email",
    "priority": "NORMAL",
    "call_id": "CALL-9f1e8a2b",
    "idempotency_key": "SES-8a4b2c1d-turn2"
  }
  ```
- **Success Response (`201 Created` or `200 OK` on repeated idempotent call):**
  ```json
  {
    "ticket_id": "SR-4471",
    "status": "OPEN",
    "customer_id": "C1023",
    "type": "service_request",
    "category": "repayment_schedule",
    "summary": "Customer requested repayment schedule statement via email",
    "priority": "NORMAL",
    "idempotency_key": "SES-8a4b2c1d-turn2",
    "created_at": "2026-10-31T12:05:00Z"
  }
  ```

### 3.7 Operations Dashboard
- **Endpoint:** `GET /api/v1/ops/calls?limit=20&offset=0`
- **Success Response (`200 OK`):**
  ```json
  {
    "total": 1,
    "calls": [
      {
        "call_id": "CALL-9f1e8a2b",
        "session_id": "SES-8a4b2c1d",
        "customer_id": "C1023",
        "started_at": "2026-10-31T12:00:00Z",
        "ended_at": null,
        "outcome": "IN_PROGRESS",
        "escalation_status": "NONE"
      }
    ]
  }
  ```
- **Endpoint:** `GET /api/v1/ops/calls/{call_id}`
- **Success Response (`200 OK`):**
  ```json
  {
    "call_id": "CALL-9f1e8a2b",
    "session_id": "SES-8a4b2c1d",
    "customer_id": "C1023",
    "started_at": "2026-10-31T12:00:00Z",
    "ended_at": null,
    "outcome": "IN_PROGRESS",
    "escalation_status": "NONE",
    "turns": [
      {
        "turn_id": "TURN-4421",
        "turn_number": 1,
        "transcript": "What is the status of my loan application?",
        "reply_text": "Your Personal Loan application APP-77 is currently in Document Verification.",
        "detected_intents": ["los_status_query"],
        "created_at": "2026-10-31T12:01:00Z"
      }
    ],
    "tickets": [],
    "audit_events": [
      {
        "event_type": "SESSION_CREATED",
        "event_status": "SUCCESS",
        "created_at": "2026-10-31T12:00:00Z"
      },
      {
        "event_type": "VERIFICATION_SUCCESS",
        "event_status": "SUCCESS",
        "created_at": "2026-10-31T12:00:30Z"
      }
    ]
  }
  ```

---

## 4. Integration Responsibilities & Boundaries

- **Member 1 (This Deliverable):** Owns database tables, session state, customer identity verification, lockout enforcement, mock banking data, ticket idempotency, call and audit persistence, and the operations dashboard endpoints.
- **Member 2 (AI Orchestration):** Connects to `app/integrations/ai_pipeline.py`. Member 2 implements STT/TTS, intent detection, and dialogue policies. The backend guarantees that sensitive banking calls cannot occur without prior server-side verification.
- **Member 3 (Frontend):** Consumes the session lifecycle endpoints, renders the assistant chat, handles verification errors/lockouts, and visualizes ticket references and call history in the operations view.
