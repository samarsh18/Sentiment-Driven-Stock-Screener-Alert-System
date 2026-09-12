"""
backend/app/database/config.py
-------------------------------
Database engine and session configuration.

Reads DATABASE_URL from the environment (via .env / .env.example).
Defaults to a local SQLite file for development and testing so the
application runs with zero infrastructure setup.

For production, set DATABASE_URL to a PostgreSQL DSN:
    DATABASE_URL=postgresql+psycopg2://user:password@host:5432/dbname

Person 2 owns this module.
Do NOT commit real credentials — use .env (git-ignored).
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load .env if present (silently ignored when absent, e.g. in CI)
load_dotenv()

# ---------------------------------------------------------------------------
# Database URL
# ---------------------------------------------------------------------------
# Default: SQLite file in the project root for local development.
# Override by setting DATABASE_URL in your .env file.
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "sqlite:///./sentiment_screener.db",
)

# ---------------------------------------------------------------------------
# SQLAlchemy engine
# ---------------------------------------------------------------------------
# check_same_thread=False is required for SQLite when the same connection
# is used across threads (e.g. during testing).  It is harmless for other
# dialects because they handle threading natively.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    echo=False,   # Set to True locally to log all SQL statements
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


def get_db():
    """
    Yield a database session and ensure it is closed after use.

    Intended as a dependency or context manager:

        with get_db() as db:
            db.query(User).all()

    When integrated with FastAPI, use as a Depends() injectable
    (Person 2 will wire this in a later review).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(target_engine=None):
    """
    Create all database tables registered on Base.metadata.

    Safe to call multiple times (tables are created IF NOT EXISTS).
    Does not delete existing data.
    """
    from backend.app.database.models import Base

    e = target_engine or engine
    Base.metadata.create_all(bind=e)
