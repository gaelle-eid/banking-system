# Banking System

A full-stack, AI-powered banking platform with two portals — **Clients** and **Employees** — sharing one backend, one database, and role-based access control (RBAC).

## Architecture
BankingSystem/
├── backend/ # Shared FastAPI app (RBAC: client / employee / admin)
│ └── app/
│ ├── agents/ # AI agents (client + employee, PydanticAI via Gateway)
│ ├── core/ # config, security, database, email, limits, audit
│ ├── models/ # SQLAlchemy models
│ ├── routers/ # API routes
│ └── schemas/ # Pydantic schemas
├── database/
│ └── init/ # Postgres init scripts
├── clients/
│ └── frontend/ # React/Vite client portal (port 5173)
├── employees/
│ └── frontend/ # React/Vite employee portal (port 5174)
├── docker-compose.yml
└── DESIGN.md # Architecture decisions, gotchas


Two React frontends talk to one shared FastAPI backend, which is the single source of truth for all banking logic. Role-based access control (not separate systems) is what distinguishes what clients vs. employees can do — this mirrors how real banking systems are built.

## Features

**Client portal**
- Registration with KYC fields (phone, DOB, address, national ID), email verification via Resend
- Multi-account banking (checking/savings, nicknamed, masked numbers)
- Deposits, withdrawals, and transfers with double-entry ledger transactions
- Loan and card requests (pending employee approval)
- Account statements
- Transaction limits (max per-transaction, daily cap, minimum balance)
- AI assistant (PydanticAI + GPT-5.2) with human-in-the-loop transfer confirmation
- Transaction and welcome emails

**Employee portal**
- Admin-created employee accounts (no public employee signup) with department/branch/job title profiles
- Approvals queue for loan and card requests
- Full audit log of every approval/rejection
- Bank-wide live reports (balances, active loans/cards, daily transaction volume)
- AI assistant for approvals, client lookups, and bank summaries — same human-in-the-loop confirmation pattern

**Shared backend**
- JWT auth + RBAC (client / employee / admin)
- Alembic migrations
- Automated test suite (pytest) covering auth, RBAC, banking logic, and AI agent guardrails

## Getting started

Requires Docker Desktop.

```bash
git clone https://github.com/gaelle-eid/banking-system.git
cd banking-system
cp .env.example .env   # fill in your own secrets — see below
docker compose up -d
```

This starts four services with one command:
- Postgres — `localhost:5433`
- FastAPI backend — `localhost:8000` (docs at `/docs`)
- Client portal — `localhost:5173`
- Employee portal — `localhost:5174`

### Environment variables

`.env` (gitignored) needs:

POSTGRES_USER=banking_admin
POSTGRES_PASSWORD=your_password
POSTGRES_DB=banking_system
DATABASE_URL=postgresql://banking_admin:your_password@db:5432/banking_system

SECRET_KEY=your_jwt_secret
ACCESS_TOKEN_EXPIRE_MINUTES=60

PYDANTIC_AI_GATEWAY_API_KEY=your_key # for the AI agents
RESEND_API_KEY=your_key # for email sending
FRONTEND_URL=http://localhost:5173

### Creating your first admin

Employees (including admins) aren't self-service — an admin creates employee accounts through the API. To bootstrap the very first admin:

1. Register a normal account through the client portal or `POST /auth/register`
2. Manually promote it in the database:
```sql
   UPDATE users SET role = 'admin', is_verified = true WHERE email = 'you@example.com';
```
3. Log into the employee portal (`localhost:5174`) with that account
4. Use `POST /admin/employees` to create further employee accounts properly

## Running tests

```bash
cd backend
docker exec -it banking_db psql -U banking_admin -d postgres -c "CREATE DATABASE banking_system_test;"
uv run pytest tests/ -v
```

## Tech stack

- **Backend**: FastAPI, SQLAlchemy (async), Alembic, PostgreSQL, `uv`
- **AI agents**: PydanticAI via the Pydantic AI Gateway (GPT-5.2), human-in-the-loop tool calling
- **Frontends**: React, Vite, Tailwind CSS v4, Recharts
- **Email**: Resend
- **Infra**: Docker Compose (4 services, one command)
- **Testing**: pytest, pytest-asyncio, httpx

## Documentation

See [`DESIGN.md`](./DESIGN.md) for architecture decisions (approval workflow, double-entry transfers, database sharing model) and known gotchas (Postgres enum migrations, event-loop pooling in async tests).

