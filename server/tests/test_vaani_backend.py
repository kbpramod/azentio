import pytest
import uuid
from app.db.seed import seed_synthetic_data
from app.models.vaani_models import AuditEvent


@pytest.mark.anyio
async def test_canonical_health(async_client):
    """Test VaaniDesk canonical health endpoint GET /health."""
    res = await async_client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "vaanidesk-backend"


@pytest.mark.anyio
async def test_session_lifecycle(async_client):
    """Test session creation, retrieval, and termination."""
    await seed_synthetic_data()

    # 1. Create a new voice session
    create_res = await async_client.post("/api/v1/sessions", json={"channel": "voice"})
    assert create_res.status_code == 201
    session_data = create_res.json()
    assert session_data["session_id"].startswith("SES-")
    assert session_data["call_id"].startswith("CALL-")
    assert session_data["verified"] is False
    assert session_data["current_state"] == "UNVERIFIED"
    assert session_data["failed_verification_attempts"] == 0
    assert session_data["locked"] is False

    session_id = session_data["session_id"]

    # 2. End the session
    end_res = await async_client.post(f"/api/v1/sessions/{session_id}/end", json={"reason": "Customer finished"})
    assert end_res.status_code == 200
    end_data = end_res.json()
    assert end_data["status"] == "ENDED"

    # 3. Verify that ended session rejects verification
    verify_res = await async_client.post(
        f"/api/v1/sessions/{session_id}/verify",
        json={"customer_id": "C1023", "dob": "1995-03-12"},
    )
    assert verify_res.status_code == 400
    assert verify_res.json()["error"]["code"] == "BAD_REQUEST"


@pytest.mark.anyio
async def test_verification_success(async_client):
    """Test successful customer identity verification via Date of Birth."""
    await seed_synthetic_data()

    # Create session
    create_res = await async_client.post("/api/v1/sessions")
    session_id = create_res.json()["session_id"]

    # Verify with correct customer C1023 and DOB
    verify_res = await async_client.post(
        f"/api/v1/sessions/{session_id}/verify",
        json={"customer_id": "C1023", "dob": "1995-03-12"},
    )
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["verified"] is True
    assert verify_data["customer_id"] == "C1023"
    assert verify_data["customer_name"] == "Alex Mercer"
    assert verify_data["current_state"] == "VERIFIED"


@pytest.mark.anyio
async def test_verification_lockout_after_three_attempts(async_client):
    """Test that 3 incorrect verification attempts permanently lock the session."""
    await seed_synthetic_data()

    # Create session
    create_res = await async_client.post("/api/v1/sessions")
    session_id = create_res.json()["session_id"]

    # Attempt 1: Wrong DOB
    res1 = await async_client.post(
        f"/api/v1/sessions/{session_id}/verify",
        json={"customer_id": "C1023", "dob": "1999-01-01"},
    )
    assert res1.status_code == 401
    err1 = res1.json()["error"]
    assert err1["code"] == "AUTH_MISMATCH"
    assert "2 attempt(s) remaining" in err1["message"]

    # Attempt 2: Wrong DOB
    res2 = await async_client.post(
        f"/api/v1/sessions/{session_id}/verify",
        json={"customer_id": "C1023", "dob": "1999-02-02"},
    )
    assert res2.status_code == 401
    err2 = res2.json()["error"]
    assert err2["code"] == "AUTH_MISMATCH"
    assert "1 attempt(s) remaining" in err2["message"]

    # Attempt 3: Wrong DOB -> Lockout
    res3 = await async_client.post(
        f"/api/v1/sessions/{session_id}/verify",
        json={"customer_id": "C1023", "dob": "1999-03-03"},
    )
    assert res3.status_code == 403
    err3 = res3.json()["error"]
    assert err3["code"] == "LOCKED"
    assert "Session locked" in err3["message"]

    # Attempt 4: Even with correct DOB, locked session remains rejected
    res4 = await async_client.post(
        f"/api/v1/sessions/{session_id}/verify",
        json={"customer_id": "C1023", "dob": "1995-03-12"},
    )
    assert res4.status_code == 403
    assert res4.json()["error"]["code"] == "LOCKED"


@pytest.mark.anyio
async def test_mock_los_applications(async_client):
    """Test Mock LOS endpoints and authorization boundaries."""
    await seed_synthetic_data()

    # 1. Create and verify session for C1023
    create_res = await async_client.post("/api/v1/sessions")
    session_id = create_res.json()["session_id"]
    await async_client.post(
        f"/api/v1/sessions/{session_id}/verify",
        json={"customer_id": "C1023", "dob": "1995-03-12"},
    )

    # 2. Query LOS applications for verified customer
    headers = {"X-Session-ID": session_id}
    los_res = await async_client.get("/api/v1/mock/los/applications?customer_id=C1023", headers=headers)
    assert los_res.status_code == 200
    los_data = los_res.json()
    assert los_data["customer_id"] == "C1023"
    assert len(los_data["applications"]) >= 2
    app_ids = [a["application_id"] for a in los_data["applications"]]
    assert "APP-77" in app_ids

    # 3. Attempting to query another customer's applications (C1024) is rejected
    cross_res = await async_client.get("/api/v1/mock/los/applications?customer_id=C1024", headers=headers)
    assert cross_res.status_code == 403
    assert cross_res.json()["error"]["code"] == "NOT_VERIFIED"


@pytest.mark.anyio
async def test_mock_lms_and_cbs(async_client):
    """Test Mock LMS loan details, repayment schedules, and CBS accounts."""
    await seed_synthetic_data()

    # Create and verify session for C1023
    create_res = await async_client.post("/api/v1/sessions")
    session_id = create_res.json()["session_id"]
    await async_client.post(
        f"/api/v1/sessions/{session_id}/verify",
        json={"customer_id": "C1023", "dob": "1995-03-12"},
    )
    headers = {"X-Session-ID": session_id}

    # 1. Test LMS Loan Details
    loan_res = await async_client.get("/api/v1/mock/lms/loans/LN-9012", headers=headers)
    assert loan_res.status_code == 200
    loan_data = loan_res.json()
    assert loan_data["loan_id"] == "LN-9012"
    assert loan_data["outstanding_amount"] == 2450000.0
    assert loan_data["emi_amount"] == 28500.0
    assert loan_data["loan_status"] == "ACTIVE"

    # 2. Test LMS Repayment Schedule
    sch_res = await async_client.get("/api/v1/mock/lms/loans/LN-9012/schedule", headers=headers)
    assert sch_res.status_code == 200
    sch_data = sch_res.json()
    assert sch_data["loan_id"] == "LN-9012"
    assert len(sch_data["schedule"]) >= 3
    assert sch_data["schedule"][0]["payment_status"] == "PAID"

    # 3. Test CBS Account Overview (Masked account number)
    cbs_res = await async_client.get("/api/v1/mock/cbs/accounts/ACC-1001", headers=headers)
    assert cbs_res.status_code == 200
    cbs_data = cbs_res.json()
    assert cbs_data["account_id"] == "ACC-1001"
    assert cbs_data["masked_account"] == "****2194"
    assert cbs_data["balance"] == 145000.50

    # 4. Test CBS Transaction
    tx_res = await async_client.get("/api/v1/mock/cbs/transactions/TX-5501", headers=headers)
    assert tx_res.status_code == 200
    tx_data = tx_res.json()
    assert tx_data["transaction_id"] == "TX-5501"
    assert tx_data["amount"] == 4500.0
    assert tx_data["transaction_type"] == "DEBIT"

    # 5. Accessing another customer's loan (LN-9020 owned by C1024) is forbidden
    unauth_loan = await async_client.get("/api/v1/mock/lms/loans/LN-9020", headers=headers)
    assert unauth_loan.status_code == 403
    assert unauth_loan.json()["error"]["code"] == "NOT_VERIFIED"


@pytest.mark.anyio
async def test_csm_ticket_idempotency(async_client):
    """Test CSM ticket creation and database-level idempotency protection."""
    await seed_synthetic_data()

    create_res = await async_client.post("/api/v1/sessions")
    session_id = create_res.json()["session_id"]
    call_id = create_res.json()["call_id"]
    await async_client.post(
        f"/api/v1/sessions/{session_id}/verify",
        json={"customer_id": "C1023", "dob": "1995-03-12"},
    )

    headers = {"X-Session-ID": session_id}
    unique_key = f"IDEMP-KEY-{uuid.uuid4().hex[:8]}"

    payload = {
        "customer_id": "C1023",
        "type": "service_request",
        "category": "repayment_schedule",
        "summary": "Customer requested repayment statement",
        "priority": "NORMAL",
        "call_id": call_id,
        "idempotency_key": unique_key,
    }

    # First ticket creation call
    t1_res = await async_client.post("/api/v1/mock/csm/tickets", headers=headers, json=payload)
    assert t1_res.status_code == 201
    t1_data = t1_res.json()
    assert "ticket_id" in t1_data
    ticket_id = t1_data["ticket_id"]

    # Duplicate call with identical idempotency key must return the exact same ticket
    t2_res = await async_client.post("/api/v1/mock/csm/tickets", headers=headers, json=payload)
    assert t2_res.status_code == 201 or t2_res.status_code == 200
    t2_data = t2_res.json()
    assert t2_data["ticket_id"] == ticket_id

    # Retrieve ticket by ID
    get_t_res = await async_client.get(f"/api/v1/mock/csm/tickets/{ticket_id}")
    assert get_t_res.status_code == 200
    assert get_t_res.json()["ticket_id"] == ticket_id


@pytest.mark.anyio
async def test_ai_pipeline_conversation_turns(async_client):
    """Test the AI turn endpoint, gating on unverified turns, and turn persistence."""
    await seed_synthetic_data()

    # 1. Create unverified session
    create_res = await async_client.post("/api/v1/sessions")
    session_id = create_res.json()["session_id"]

    # 2. Unverified turn asking for loan balance
    unverified_turn = await async_client.post(
        f"/api/v1/sessions/{session_id}/turn",
        json={"text": "What is my loan balance?", "input_type": "voice_transcript"},
    )
    assert unverified_turn.status_code == 200
    turn1_data = unverified_turn.json()
    assert "verify your identity" in turn1_data["reply_text"].lower()
    assert turn1_data["verified"] is False

    # 3. Verify session
    await async_client.post(
        f"/api/v1/sessions/{session_id}/verify",
        json={"customer_id": "C1023", "dob": "1995-03-12"},
    )

    # 4. Verified turn asking for loan status
    verified_turn = await async_client.post(
        f"/api/v1/sessions/{session_id}/turn",
        json={"text": "What is the status of my loan application?", "input_type": "voice_transcript"},
    )
    assert verified_turn.status_code == 200
    turn2_data = verified_turn.json()
    assert turn2_data["verified"] is True
    assert "application" in turn2_data["reply_text"].lower()
    assert "APP-77" in turn2_data["reply_text"] or "DOC_VERIFICATION" in turn2_data["reply_text"] or "Alex" in turn2_data["reply_text"]


@pytest.mark.anyio
async def test_session_escalation(async_client):
    """Test call escalation to human agent and escalation ticket generation."""
    await seed_synthetic_data()

    create_res = await async_client.post("/api/v1/sessions")
    session_id = create_res.json()["session_id"]

    esc_res = await async_client.post(
        f"/api/v1/sessions/{session_id}/escalate",
        json={
            "reason": "Customer dissatisfied with overdue fee clarification",
            "category": "complaint",
            "priority": "HIGH",
        },
    )
    assert esc_res.status_code == 200
    esc_data = esc_res.json()
    assert esc_data["escalated"] is True
    assert esc_data["escalation_id"].startswith("ESC-")
    assert esc_data["ticket_id"].startswith("SR-")


@pytest.mark.anyio
async def test_operations_dashboard_apis(async_client):
    """Test operations dashboard listing and detail endpoints."""
    await seed_synthetic_data()

    # 1. Create a session and record a turn
    create_res = await async_client.post("/api/v1/sessions")
    session_id = create_res.json()["session_id"]
    call_id = create_res.json()["call_id"]

    await async_client.post(
        f"/api/v1/sessions/{session_id}/turn",
        json={"text": "Hello assistant", "input_type": "text"},
    )

    # 2. Ops: List calls
    calls_res = await async_client.get("/api/v1/ops/calls")
    assert calls_res.status_code == 200
    calls_data = calls_res.json()
    assert calls_data["total"] >= 1
    found_call = next((c for c in calls_data["calls"] if c["call_id"] == call_id), None)
    assert found_call is not None

    # 3. Ops: Get call details
    detail_res = await async_client.get(f"/api/v1/ops/calls/{call_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["call_id"] == call_id
    assert len(detail_data["turns"]) >= 1
    assert len(detail_data["audit_events"]) >= 1

    # 4. Ops: List tickets
    tickets_res = await async_client.get("/api/v1/ops/tickets")
    assert tickets_res.status_code == 200
    assert tickets_res.json()["total"] >= 1

    # 5. Ops: List escalations
    esc_res = await async_client.get("/api/v1/ops/escalations")
    assert esc_res.status_code == 200
    assert isinstance(esc_res.json()["escalations"], list)

