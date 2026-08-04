from fastapi import FastAPI

app = FastAPI(title="Banking System API")


@app.get("/health")
async def health_check():
    return {"status": "ok"}