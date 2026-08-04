from fastapi import FastAPI
from app.routers import auth

app = FastAPI(title="Banking System API")

app.include_router(auth.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}