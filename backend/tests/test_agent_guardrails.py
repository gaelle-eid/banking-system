import pytest
from tests.helpers import create_verified_user


async def create_account(client, token, acc_type="checking"):
    response = await client.post(
        "/accounts",
        json={"type": acc_type, "currency": "USD"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return response.json()


@pytest.mark.asyncio
async def test_agent_chat_requires_auth(client):
    response = await client.post("/agent/client/chat", json={"message": "hi"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_employee_agent_blocked_for_clients(client, db_session):
    token = await create_verified_user(client, db_session, email="agentclient@example.com", role="client")

    response = await client.post(
        "/agent/employee/chat",
        json={"message": "list pending approvals"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_agent_transfer_does_not_execute_until_confirmed(client, db_session):
    """The core human-in-the-loop guarantee: proposing a transfer via the
    agent must NOT move any money until the client explicitly confirms."""
    token = await create_verified_user(client, db_session, email="agenttx@example.com", role="client")
    account = await create_account(client, token)

    await client.post(
        "/transactions/deposit",
        json={"account_id": account["id"], "amount": 100},
        headers={"Authorization": f"Bearer {token}"},
    )

    chat_response = await client.post(
        "/agent/client/chat",
        json={"message": f"Transfer 20 from my checking account to account number 0000000000"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert chat_response.status_code == 200

    # balance must be unchanged - agent should only PROPOSE, never execute directly
    check = await client.get("/accounts/me", headers={"Authorization": f"Bearer {token}"})
    balance = next(a["balance"] for a in check.json() if a["id"] == account["id"])
    assert float(balance) == 100.0


@pytest.mark.asyncio
async def test_confirming_unknown_action_returns_404(client, db_session):
    token = await create_verified_user(client, db_session, email="agentaction@example.com", role="client")

    response = await client.post(
        "/agent/client/actions/00000000-0000-0000-0000-000000000000/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404