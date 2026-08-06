import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    response = await client.post("/auth/register", json={
        "email": "testuser1@example.com",
        "password": "StrongPass123!",
        "full_name": "Test User",
        "phone": "+96170123456",
        "date_of_birth": "1998-05-20",
        "address": "123 Test St",
        "national_id": "TEST1234",
        "accepted_terms": True,
        "role": "client",
    })
    assert response.status_code == 201
    assert response.json()["email"] == "testuser1@example.com"


@pytest.mark.asyncio
async def test_register_weak_password_rejected(client):
    response = await client.post("/auth/register", json={
        "email": "testuser2@example.com",
        "password": "weak",
        "full_name": "Test User",
        "phone": "+96170123456",
        "date_of_birth": "1998-05-20",
        "address": "123 Test St",
        "national_id": "TEST1234",
        "accepted_terms": True,
        "role": "client",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_underage_rejected(client):
    response = await client.post("/auth/register", json={
        "email": "testuser3@example.com",
        "password": "StrongPass123!",
        "full_name": "Test User",
        "phone": "+96170123456",
        "date_of_birth": "2015-01-01",
        "address": "123 Test St",
        "national_id": "TEST1234",
        "accepted_terms": True,
        "role": "client",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_blocked_before_verification(client):
    await client.post("/auth/register", json={
        "email": "testuser4@example.com",
        "password": "StrongPass123!",
        "full_name": "Test User",
        "phone": "+96170123456",
        "date_of_birth": "1998-05-20",
        "address": "123 Test St",
        "national_id": "TEST1234",
        "accepted_terms": True,
        "role": "client",
    })
    response = await client.post("/auth/login", json={
        "email": "testuser4@example.com",
        "password": "StrongPass123!",
    })
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_duplicate_email_rejected(client):
    payload = {
        "email": "dup@example.com",
        "password": "StrongPass123!",
        "full_name": "Test User",
        "phone": "+96170123456",
        "date_of_birth": "1998-05-20",
        "address": "123 Test St",
        "national_id": "TEST1234",
        "accepted_terms": True,
        "role": "client",
    }
    r1 = await client.post("/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/auth/register", json=payload)
    assert r2.status_code == 400