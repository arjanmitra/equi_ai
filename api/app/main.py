"""FastAPI entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.database import init_db
from app.routers import extract, funds


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create tables if they don't exist
    yield


app = FastAPI(title="Allocator Memo Builder API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(extract.router)
app.include_router(funds.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "llm_available": settings.llm_available}
