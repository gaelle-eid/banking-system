from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.scheduler import start_scheduler, stop_scheduler
from app.routers import auth, accounts, transactions, loans, cards, statements, agent, approvals, audit, employees, reports, admin, employee_agent, registrations, knowledge, goals,fraud, funding_sources
app = FastAPI(title="Banking System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(loans.router)
app.include_router(cards.router)
app.include_router(statements.router)
app.include_router(agent.router)
app.include_router(approvals.router)
app.include_router(audit.router)
app.include_router(employees.router)
app.include_router(reports.router)
app.include_router(admin.router)
app.include_router(employee_agent.router)
app.include_router(registrations.router)
app.include_router(knowledge.router)
app.include_router(goals.router)
app.include_router(fraud.router)
app.include_router(funding_sources.router)

@app.on_event("startup")
async def on_startup():
    start_scheduler()


@app.on_event("shutdown")
async def on_shutdown():
    stop_scheduler()


@app.get("/health")
async def health_check():
    return {"status": "ok"}