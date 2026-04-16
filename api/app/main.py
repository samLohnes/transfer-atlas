"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database import engine
from app.routers import clubs, countries, filters, flows, metadata, players

app = FastAPI(title="TransferAtlas API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(metadata.router)
app.include_router(countries.router)
app.include_router(flows.router)
app.include_router(clubs.router)
app.include_router(filters.router)
app.include_router(players.router)


@app.get("/api/v1/health")
def health_check() -> dict:
    """Verify the API is running and can reach PostgreSQL."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}
