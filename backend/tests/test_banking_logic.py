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
async def test_deposit_increases_balance(client, db_session):
    token = await create_verified_user(client, db_session, email="bank1@example.com")
    account = await create_account(client, token)

    response = await client.post(
        "/transactions/deposit",
        json={"account_id": account["id"], "amount": 100},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201

    check = await client.get("/accounts/me", headers={"Authorization": f"Bearer {token}"})
    balance = next(a["balance"] for a in check.json() if a["id"] == account["id"])
    assert float(balance) == 100.0


@pytest.mark.asyncio
async def test_withdraw_insufficient_funds_rejected(client, db_session):
    token = await create_verified_user(client, db_session, email="bank2@example.com")
    account = await create_account(client, token)

    response = await client.post(
        "/transactions/withdraw",
        json={"account_id": account["id"], "amount": 50},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "Insufficient funds" in response.json()["detail"]


@pytest.mark.asyncio
async def test_transfer_moves_money_between_accounts(client, db_session):
    token = await create_verified_user(client, db_session, email="bank3@example.com")
    acc_a = await create_account(client, token, "checking")
    acc_b = await create_account(client, token, "savings")

    await client.post(
        "/transactions/deposit",
        json={"account_id": acc_a["id"], "amount": 200},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = await client.post(
        "/transactions/transfer",
        json={"from_account_id": acc_a["id"], "to_account_id": acc_b["id"], "amount": 50},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    txs = response.json()
    assert len(txs) == 2
    assert txs[0]["type"] == "transfer_debit"
    assert txs[1]["type"] == "transfer_credit"
    assert txs[0]["transfer_group_id"] == txs[1]["transfer_group_id"]

    check = await client.get("/accounts/me", headers={"Authorization": f"Bearer {token}"})
    balances = {a["id"]: float(a["balance"]) for a in check.json()}
    assert balances[acc_a["id"]] == 150.0
    assert balances[acc_b["id"]] == 50.0


@pytest.mark.asyncio
async def test_transaction_over_max_limit_rejected(client, db_session):
    token = await create_verified_user(client, db_session, email="bank4@example.com")
    account = await create_account(client, token)

    response = await client.post(
        "/transactions/deposit",
        json={"account_id": account["id"], "amount": 15000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400
    assert "maximum allowed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_client_cannot_access_other_clients_account(client, db_session):
    token_a = await create_verified_user(client, db_session, email="banka@example.com")
    token_b = await create_verified_user(client, db_session, email="bankb@example.com")

    account_a = await create_account(client, token_a)

    response = await client.get(
        f"/accounts/{account_a['id']}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 403