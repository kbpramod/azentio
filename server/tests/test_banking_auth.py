import time
import pytest
from app.main import init_database


@pytest.mark.anyio
async def test_auth_and_banking_flow(async_client):
    # Initialize DB tables
    await init_database()

    # 1. Login with seeded demo user
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "customer@azentio.com", "password": "password123"},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["user"]["email"] == "customer@azentio.com"
    initial_credits = login_data["user"]["ai_credits"]
    assert initial_credits >= 0

    token = login_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Test /auth/me
    me_res = await async_client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["full_name"] == "Alex Mercer"

    # 3. Test /banking/account
    account_res = await async_client.get("/api/v1/banking/account", headers=headers)
    assert account_res.status_code == 200
    account_data = account_res.json()
    assert account_data["account_number"].startswith("AZ-")

    # 4. Test /banking/transactions
    tx_res = await async_client.get("/api/v1/banking/transactions", headers=headers)
    assert tx_res.status_code == 200
    tx_data = tx_res.json()
    assert len(tx_data) >= 1

    # 5. Test AI Customer Service Agent chat (uses AI credits)
    agent_res = await async_client.post(
        "/api/v1/agent/chat",
        headers=headers,
        json={"message": "What is my account balance?"},
    )
    assert agent_res.status_code == 200
    agent_data = agent_res.json()
    assert "reply" in agent_data
    assert agent_data["ai_credits_used"] == 5
    assert agent_data["remaining_credits"] == initial_credits - 5

    # 6. Test registration of a new customer
    unique_email = f"user_{int(time.time())}@example.com"
    reg_res = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": "securepassword99",
            "full_name": "Sarah Connor",
            "initial_deposit": 500.0,
        },
    )
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert reg_data["user"]["email"] == unique_email
    assert reg_data["user"]["balance"] == 500.0
    assert reg_data["user"]["ai_credits"] == 500

    # 7. Test logout
    logout_res = await async_client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 200
