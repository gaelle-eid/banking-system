from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, accounts, transactions, loans, cards, statements, agent

app = FastAPI(title="Banking System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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


@app.get("/health")
async def health_check():
    return {"status": "ok"}