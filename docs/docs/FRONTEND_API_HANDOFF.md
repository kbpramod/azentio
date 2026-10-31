# Frontend Team Handoff: VaaniDesk API Integration

**To:** Member 3 (Frontend Engineer)  
**From:** Member 1 (Senior Backend Engineer)  
**Date:** 2026-10-31  
**Project:** VaaniDesk — AI-Powered Voice Customer Service Assistant  
**Backend Base URL:** `http://127.0.0.1:8000` (API prefix: `/api/v1`)  
**Interactive API Docs:** `http://127.0.0.1:8000/docs` (OpenAPI Swagger) & `http://127.0.0.1:8000/redoc`  

---

## 1. What You Need to Know

The VaaniDesk backend has been upgraded with a zero-dependency, local-ready SQLite database architecture containing comprehensive synthetic banking data. All existing React portal endpoints (`/auth/login`, `/auth/me`, `/banking/account`, `/banking/transactions`, `/agent/chat`) remain **100% backward compatible**, while a full suite of **Voice & Agent Session APIs**, **Customer Verification**, **Mock Banking Services (LOS / LMS / CBS)**, **CSM Tickets**, and **Operations Dashboard APIs** are now live.

Complete specifications are available in:
- Markdown: `docs/VAANIDESK_API_DOCUMENTATION.md`
- PDF: `docs/VAANIDESK_API_DOCUMENTATION.pdf`
- Formal Contract: `docs/API_CONTRACT.md`

---

## 2. Quick Start: Running the Backend Locally

```bash
# 1. Navigate to the server directory
cd azentio/server

# 2. Activate the virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Seed synthetic banking data (repeatable, idempotent)
python -m app.db.seed

# 4. Start the FastAPI development server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Health check verification:
```bash
curl http://127.0.0.1:8000/health
# Response: {"status": "ok", "service": "vaanidesk-backend"}
```

---

## 3. Core Voice & Chat Assistant Integration Flow

The voice/chat assistant follows a strictly server-controlled session lifecycle:

```
[1. Create Session]   --> POST /api/v1/sessions
                          └─ Returns session_id and call_id

[2. Identity Check]   --> POST /api/v1/sessions/{session_id}/verify
                          └─ Body: {"customer_id": "C1023", "dob": "1995-03-12"}
                          └─ 3 failed attempts permanently lock session (HTTP 403 LOCKED)

[3. Submit Turn]      --> POST /api/v1/sessions/{session_id}/turn
                          └─ Body: {"text": "What is my loan status?", "input_type": "voice_transcript"}
                          └─ Returns AI response, detected intents, updated state

[4. Human Handoff]    --> POST /api/v1/sessions/{session_id}/escalate
                          └─ Body: {"reason": "Customer requested human supervisor"}
                          └─ Creates escalation and support ticket

[5. End Call]         --> POST /api/v1/sessions/{session_id}/end
                          └─ Closes session and records call outcome
```

---

## 4. Ready-to-Use Frontend Integration Snippets

### A. Creating a Voice/Chat Session
```javascript
const response = await fetch('http://127.0.0.1:8000/api/v1/sessions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ channel: 'web_voice' })
});
const session = await response.json();
// Store session.session_id for subsequent requests
console.log('Active Session ID:', session.session_id);
```

### B. Customer Identity Verification (DOB Check)
```javascript
const verifyResponse = await fetch(`http://127.0.0.1:8000/api/v1/sessions/${sessionId}/verify`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    customer_id: 'C1023',
    dob: '1995-03-12' // Format: YYYY-MM-DD
  })
});

if (verifyResponse.ok) {
  const data = await verifyResponse.json();
  console.log('Customer verified:', data.customer_name);
} else {
  const err = await verifyResponse.json();
  if (err.error?.code === 'LOCKED') {
    alert('Session is locked due to 3 failed attempts. Please contact branch support.');
  } else {
    alert(`Verification failed: ${err.error?.message}`);
  }
}
```

### C. Sending a Conversation Turn
```javascript
const turnResponse = await fetch(`http://127.0.0.1:8000/api/v1/sessions/${sessionId}/turn`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    text: userInputText,
    input_type: 'voice_transcript'
  })
});
const turnData = await turnResponse.json();
console.log('Assistant Reply:', turnData.reply_text);
```

### D. Retrieving Call History for Operations Dashboard
```javascript
const callsResponse = await fetch('http://127.0.0.1:8000/api/v1/ops/calls?limit=25');
const { calls } = await callsResponse.json();
```

---

## 5. Synthetic Test Data Cheat Sheet

| Customer ID | Customer Name | Date of Birth | Associated Loan / Account | Test Scenario |
|---|---|---|---|---|
| `C1023` | Alex Mercer | `1995-03-12` | Loan: `LN-9012` (Home Loan), Application: `APP-77` | Verified customer, active loan, pending salary slip doc |
| `C1024` | Priya Sharma | `1990-08-25` | Account: `ACC-1002`, Application: `APP-88` | Multi-account customer, loan approved |
| `C1099` | Locked Test User | `1985-01-01` | N/A | Use wrong DOB 3 times to test lockout handling |

---

## 6. Support & Feedback

If you encounter any discrepancies between frontend expectations and the API responses, please refer to Swagger UI at `http://127.0.0.1:8000/docs` or check `docs/VAANIDESK_API_DOCUMENTATION.md`. Member 1 is actively monitoring backend test suites to ensure 100% stability.
