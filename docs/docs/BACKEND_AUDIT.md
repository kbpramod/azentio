# VaaniDesk (Azentio Banking System) — Backend Architecture & Codebase Audit

**Date:** 2026-10-31  
**Role:** Member 1 — Senior Backend Engineer  
**Project:** VaaniDesk — AI-Powered Voice Customer Service Assistant for Banking and Financial Services  

---

## 1. Executive Summary

This audit assesses the existing repository (`c:\Azentio_final`) to establish the baseline implementation status against the **VaaniDesk Member 1 Backend** responsibilities. The repository contains a monorepo setup under `azentio/`:
- `azentio/server`: A FastAPI backend written with SQLAlchemy async ORM, Pydantic v2, and JWT authentication.
- `azentio/client`: A React/Vite single-page application demonstrating customer dashboard features, transaction views, fund transfers, and an AI agent chat interface.

The existing codebase was previously tailored toward an online banking customer portal connected strictly to PostgreSQL Neon. For VaaniDesk, Member 1 must introduce:
- SQLite support for local zero-dependency prototyping while retaining PostgreSQL compatibility.
- Comprehensive synthetic banking entities (Customers, Loan Applications, Loans, Repayment Schedules, CBS Accounts, CBS Transactions).
- Server-side voice/agent session lifecycle management (`/api/v1/sessions`).
- Server-side customer verification with failure attempt tracking and lockout after 3 failed attempts (`/api/v1/sessions/{session_id}/verify`).
- Mock LOS (Loan Origination System), LMS (Loan Management System), and CBS APIs.
- Customer Service Management (CSM) ticket creation with atomic idempotency enforcement.
- Call history persistence and audit logging with sensitive data redaction.
- Operations dashboard APIs (`/api/v1/ops/*`).
- Integration adapter for Member 2's AI orchestration pipeline.

---

## 2. Detailed Audit Points

### 2.1 What Is Already Implemented

1. **FastAPI Application Setup:**
   - Central entry point in `azentio/server/app/main.py`.
   - Central router aggregation in `azentio/server/app/api/v1/api.py`.
   - CORS middleware configured via `BACKEND_CORS_ORIGINS`.
   - Health check endpoint at `GET /api/v1/health`.

2. **Security & Authentication Base:**
   - JWT token generation (`create_access_token`) and verification (`get_current_user`) in `azentio/server/app/core/security.py`.
   - Password hashing with `bcrypt` (`hash_password`, `verify_password`).
   - Customer registration, login, logout, and `/me` routes in `azentio/server/app/api/v1/endpoints/auth.py`.

3. **Basic Banking Endpoints (Customer Portal):**
   - Account overview `GET /api/v1/banking/account`.
   - Transaction history `GET /api/v1/banking/transactions`.
   - Transfer funds `POST /api/v1/banking/transfer`.
   - Deposit funds `POST /api/v1/banking/deposit`.

4. **Basic Agent Chat:**
   - Endpoint `POST /api/v1/agent/chat` with rule-based fallback and AI credit deduction.

5. **Client Application:**
   - Functional React/Vite UI with `AuthCard`, `Dashboard`, `AgentChat`, and `TransferModal`.

---

### 2.2 What Is Partially Implemented

1. **Database Session & Engine:**
   - `azentio/server/app/db/session.py` is configured strictly for PostgreSQL Neon with hardcoded SSL context and `postgresql+asyncpg` driver requirement. It throws a 500 error if `DATABASE_URL` is empty.
   - `aiosqlite` is present in `requirements.txt`, but not wired into `session.py`.
2. **Health Check:**
   - `GET /api/v1/health` exists, but the canonical root `GET /health` required by VaaniDesk specification is missing.
3. **Database Entities:**
   - Only `users` and `transactions` tables exist in `app/models/`. Missing are: `customers`, `loan_applications`, `loans`, `emi_schedules`, `accounts`, `sessions`, `calls`, `conversation_turns`, `tickets`, and `audit_events`.
4. **Seed Data:**
   - `main.py` contains inline seeding for a single demo user (`customer@azentio.com`). A modular, repeatable synthetic seed script for VaaniDesk test scenarios is missing.

---

### 2.3 What Is Missing (Member 1 Scope)

1. **Session Management Endpoints:**
   - `POST /api/v1/sessions` (Create session & initialize call)
   - `POST /api/v1/sessions/{session_id}/verify` (DOB verification with lockout)
   - `POST /api/v1/sessions/{session_id}/turn` (Turn processing via AI adapter)
   - `POST /api/v1/sessions/{session_id}/escalate` (Escalation to human agent)
   - `POST /api/v1/sessions/{session_id}/end` (Session & call termination)

2. **Mock Banking System Integrations:**
   - **LOS:** `GET /api/v1/mock/los/applications?customer_id=C1023`
   - **LMS:** `GET /api/v1/mock/lms/loans/{loan_id}` and `GET /api/v1/mock/lms/loans/{loan_id}/schedule`
   - **CBS:** `GET /api/v1/mock/cbs/accounts/{account_id}` and `GET /api/v1/mock/cbs/transactions/{transaction_id}`

3. **CSM Ticket System:**
   - `POST /api/v1/mock/csm/tickets` (with database-enforced idempotency key)
   - `GET /api/v1/mock/csm/tickets/{ticket_id}`

4. **Operations Dashboard APIs:**
   - `GET /api/v1/ops/calls` (List calls with filters)
   - `GET /api/v1/ops/calls/{call_id}` (Call details with conversation turns and trace)
   - `GET /api/v1/ops/tickets` (List tickets with status and priority filters)
   - `GET /api/v1/ops/escalations` (List active escalations)

5. **AI Pipeline Integration Adapter:**
   - `app/integrations/ai_pipeline.py` providing a clean boundary for Member 2's orchestration pipeline with deterministic fallback.

6. **Audit & Call Logging System:**
   - Server-side audit event logging with sensitive PII/credential redaction.

7. **Automated Testing Suite:**
   - Tests covering all required endpoints, session state machine, lockout mechanism, idempotency, and authorization boundaries.

8. **Mandatory Documentation:**
   - `docs/API_CONTRACT.md`
   - `docs/VAANIDESK_API_DOCUMENTATION.md`
   - `docs/VAANIDESK_API_DOCUMENTATION.pdf`
   - `docs/FRONTEND_API_HANDOFF.md`

---

### 2.4 What Is Broken or Inconsistent

1. **Database Fallback:**
   - When running locally without a Neon PostgreSQL connection string, backend routes fail with `HTTP 500: PostgreSQL Neon database not configured`.
   - Solution: Enhance `app/db/session.py` and `app/core/config.py` to seamlessly default to SQLite (`sqlite+aiosqlite:///./azentio_banking.db`) when `DATABASE_URL` is empty or begins with `sqlite`, while preserving full asyncpg Neon support when a postgres connection is provided.
2. **Error Response Format:**
   - Current endpoints use standard FastAPI HTTPException responses `{"detail": "..."}`.
   - VaaniDesk contract specifies structured errors:
     ```json
     {
       "error": {
         "code": "AUTH_MISMATCH",
         "message": "Customer verification is required.",
         "retryable": false
       }
     }
     ```
   - Solution: Introduce a custom exception handler and error models in `app/core/exceptions.py`.

---

### 2.5 Reusability and File Strategy

| File | Status | Action |
|---|---|---|
| `azentio/server/app/main.py` | Working | Modify: add root `/health`, register new routers (`sessions`, `mock_los`, `mock_lms`, `mock_cbs`, `csm`, `ops`), enable SQLite default fallback. |
| `azentio/server/app/core/config.py` | Working | Modify: add default SQLite DB URL and session configuration. |
| `azentio/server/app/core/security.py` | Working | Reuse: keep JWT & bcrypt, add session token / helper utilities. |
| `azentio/server/app/core/exceptions.py` | Missing | Create: structured VaaniDesk error handler. |
| `azentio/server/app/db/session.py` | Needs fix | Modify: support both SQLite (`aiosqlite`) and PostgreSQL (`asyncpg`). |
| `azentio/server/app/models/user.py` | Working | Reuse: preserve customer portal user model. |
| `azentio/server/app/models/transaction.py` | Working | Reuse: preserve portal transactions. |
| `azentio/server/app/models/vaani_models.py` | Missing | Create: Customer, LoanApplication, Loan, EMISchedule, Account, Transaction, Session, Call, Turn, Ticket, AuditEvent. |
| `azentio/server/app/db/seed.py` | Missing | Create: repeatable synthetic seeding for testing & dev. |
| `azentio/server/app/schemas/*` | Partial | Create schemas for sessions, verification, los, lms, cbs, tickets, and ops. |
| `azentio/server/app/services/*` | Partial | Create domain services (`session_service.py`, `verification_service.py`, `banking_service.py`, `ticket_service.py`, `ops_service.py`, `audit_service.py`). |
| `azentio/server/app/api/v1/endpoints/*` | Partial | Add endpoints for `sessions.py`, `mock_banking.py`, `csm.py`, `ops.py`. |
| `azentio/server/app/integrations/ai_pipeline.py` | Missing | Create: Member 2 AI integration adapter. |

---

### 2.6 SQL Schema Feasibility for Required Workflows

The planned entities directly map to relational tables and support all required business workflows:
- Customer verification: `Customer.customer_id` and `Customer.dob` validated against request.
- Session lockout: `Session.failed_verification_attempts` incremented atomically; when >= 3, `Session.locked = True`.
- Idempotent ticket creation: `Ticket.idempotency_key` with a unique index.
- Sensitive audit logs: `AuditEvent` table storing sanitized metadata with automated redaction.

---

### 2.7 Authentication & Session Security for Prototype

The prototype requires server-side session authorization:
- Sessions are created via `POST /api/v1/sessions` and stored in SQLite.
- Client-supplied `verified: true` flags will be completely rejected; verification status is exclusively determined and updated by the server.
- Verification lockout prevents brute-forcing DOB.
- Sensitive banking operations verify that `session.verified is True` and that the requested account/loan belongs to `session.customer_id`.

---

### 2.8 API Contract Alignment

Existing routes (`/api/v1/auth/*`, `/api/v1/banking/*`, `/api/v1/agent/chat`) remain intact to ensure zero regression for the React client.
The new VaaniDesk routes will be mounted under `/api/v1` and documented extensively in `docs/API_CONTRACT.md` and `docs/VAANIDESK_API_DOCUMENTATION.md`.
