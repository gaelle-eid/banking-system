# Banking System

Full-stack banking platform with two portals — Clients and Employees — sharing one backend and one database.

## Structure

BankingSystem/
├── backend/          # shared FastAPI app (RBAC: client / employee / admin)
├── database/         # Postgres init/seed scripts
├── clients/frontend/ # React/Vite client portal
├── employees/frontend/ # React/Vite employee/admin portal
├── docker-compose.yml
└── .env.example

## Getting Started

    docker compose up --build