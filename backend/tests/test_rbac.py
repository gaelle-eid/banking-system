import pytest
from tests.helpers import create_verified_user


@pytest.mark.asyncio
async def test_client_blocked_from_approvals(client, db_session):
    token = await create_verified_user(client, db_session, email="rbac_client@example.com", role="client")

    response = await client.get("/approvals", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_client_blocked_from_audit_logs(client, db_session):
    token = await create_verified_user(client, db_session, email="rbac_client2@example.com", role="client")

    response = await client.get("/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_client_blocked_from_admin_users(client, db_session):
    token = await create_verified_user(client, db_session, email="rbac_client3@example.com", role="client")

    response = await client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_employee_can_access_approvals(client, db_session):
    token = await create_verified_user(client, db_session, email="rbac_emp@example.com", role="employee")

    response = await client.get("/approvals", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_employee_blocked_from_admin_only_endpoints(client, db_session):
    # employees can approve/reject, but admin-only user management should
    # still be off-limits to them
    token = await create_verified_user(client, db_session, email="rbac_emp2@example.com", role="employee")

    response = await client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client):
    response = await client.get("/approvals")
    assert response.status_code == 401