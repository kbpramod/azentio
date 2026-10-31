import time
import pytest
from app.core.config import settings
from app.main import init_database


@pytest.mark.anyio
async def test_cookie_auth_and_banking_flow(async_client):
    # Initialize DB tables
    await init_database()

    # 1. Login with seeded demo user
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "customer@azentio.com", "password": "password123"},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["user"]["email"] == "customer@azentio.com"

    # Verify HttpOnly cookies are set in response
    assert settings.COOKIE_ACCESS_NAME in login_res.cookies
    assert settings.COOKIE_REFRESH_NAME in login_res.cookies

    # 2. Test /auth/me authenticated purely via Cookie (no header!)
    me_res = await async_client.get("/api/v1/auth/me")
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["full_name"] == "Alex Mercer"

    # 3. Test /banking/account
    account_res = await async_client.get("/api/v1/banking/account")
    assert account_res.status_code == 200
    account_data = account_res.json()
    assert account_data["account_number"].startswith("AZ-")

    # 4. Test /banking/transactions
    tx_res = await async_client.get("/api/v1/banking/transactions")
    assert tx_res.status_code == 200
    tx_data = tx_res.json()
    assert len(tx_data) >= 1

    # 5. Test AI Customer Service Agent chat (uses AI credits)
    agent_res = await async_client.post(
        "/api/v1/agent/chat",
        json={"message": "What is my account balance?"},
    )
    assert agent_res.status_code == 200
    agent_data = agent_res.json()
    assert "reply" in agent_data
    assert agent_data["ai_credits_used"] == 5

    # 6. Test Refresh Token endpoint
    refresh_res = await async_client.post("/api/v1/auth/refresh")
    assert refresh_res.status_code == 200
    assert settings.COOKIE_ACCESS_NAME in refresh_res.cookies

    # 7. Test Logout (clears cookies)
    logout_res = await async_client.post("/api/v1/auth/logout")
    assert logout_res.status_code == 200

    # 8. Test registration of a new customer
    unique_email = f"customer_{int(time.time())}@example.com"
    reg_res = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": "securepassword99",
            "full_name": "Jordan Lee",
            "initial_deposit": 750.0,
        },
    )
    assert reg_res.status_code == 201
    assert settings.COOKIE_ACCESS_NAME in reg_res.cookies
    reg_data = reg_res.json()
    assert reg_data["user"]["email"] == unique_email
    assert reg_data["user"]["balance"] == 750.0
