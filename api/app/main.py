"""FastAPI entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.database import init_db
from app.routers import (
    analysis,
    extract,
    funds,
    mandates,
    memo,
    metrics,
    returns,
    runs,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create tables if they don't exist
    yield


app = FastAPI(title="Allocator Memo Builder API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # Any localhost port — the Next dev server may land on 3000, 3001, ...
    allow_origin_regex=r"http://localhost:\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis.router)
app.include_router(extract.router)
app.include_router(funds.router)
app.include_router(mandates.router)
app.include_router(memo.router)
app.include_router(metrics.router)
app.include_router(returns.router)
app.include_router(runs.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "llm_available": settings.llm_available}
