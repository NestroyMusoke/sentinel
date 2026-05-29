import os
from fastapi import FastAPI
from dotenv import load_dotenv
from backend.db.mongo import async_db

load_dotenv()

app = FastAPI(
    title="Sentinel",
    description="Autonomous outbreak coordination intelligence",
    version="1.0.0"
)

@app.get("/health")
async def health_check():
    try:
        await async_db.command("ping")
        return {
            "status": "operational",
            "system": "sentinel",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "degraded",
            "system": "sentinel",
            "database": f"error: {str(e)}"
        }

@app.get("/")
async def root():
    return {
        "system": "SENTINEL",
        "tagline": "Autonomous outbreak coordination intelligence",
        "version": "1.0.0"
    }