"""SQLAlchemy engine, session, and declarative base.

SQLite by default (zero-infra for the take-home); swappable to Postgres via
DATABASE_URL. Schema is created with `create_all` on startup — no Alembic yet,
a deliberate scope cut. The persistence service takes a Session explicitly, so
tests can bind their own in-memory engine without touching this global one.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./equi_ai.db")

# check_same_thread is a SQLite-only concern (FastAPI may touch the session from
# a different thread than it was created on).
_connect_args = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """Create tables. Importing models registers them on Base.metadata."""
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
