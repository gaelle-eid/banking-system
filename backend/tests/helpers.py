from sqlalchemy import select
from app.models.models import User


async def create_verified_user(client, db_session, email="verified@example.com", password="StrongPass123!", role="client"):
    await client.post("/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Verified User",
        "phone": "+96170123456",
        "date_of_birth": "1998-05-20",
        "address": "123 Test St",
        "national_id": "TESTID001",
        "accepted_terms": True,
        "role": role,
    })

    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    user.is_verified = True
    await db_session.commit()

    login_res = await client.post("/auth/login", json={"email": email, "password": password})
    token = login_res.json()["access_token"]
    return token