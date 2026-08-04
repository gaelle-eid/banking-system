from fastapi import FastAPI
from app.routers import auth, accounts, transactions

app = FastAPI(title="Banking System API")

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(transactions.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}