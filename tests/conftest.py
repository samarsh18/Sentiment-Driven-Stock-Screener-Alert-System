"""
tests/conftest.py
------------------
Shared pytest fixtures for all tests.

Strategy
--------
We use a single persistent in-memory SQLite engine. Each test runs its
own transaction which is rolled back afterwards, ensuring isolation.

CRITICAL: The `client` fixture depends on `db_session`. Both use the
SAME Session object, so:
- Data inserted via `db_session.add(...)` followed by `db_session.flush()`
  is immediately visible to HTTP route handlers (same session / same transaction).
- Data inserted via HTTP (POST /api/...) is visible to subsequent queries
  via `db_session`.

Important: Tests must call `db_session.flush()` (NOT `db_session.commit()`)
after seeding data so the session sees it without closing the transaction.

get_db identity
---------------
All routers Depends() on `backend.app.database.config.get_db`.
`api/deps.py` re-exports that same object.
The conftest overrides that same canonical function so the override applies.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# The CANONICAL get_db — must match what all routers Depends() on
from backend.app.database.config import get_db
from backend.app.database.models import Base
from backend.app.main import create_app

# ---------------------------------------------------------------------------
# Shared engine — created once, all tests use it
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite:///:memory:"

_test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
Base.metadata.create_all(bind=_test_engine)

_TestingSessionLocal = sessionmaker(
    bind=_test_engine, autocommit=False, autoflush=False
)


# ---------------------------------------------------------------------------
# Per-test session — rolled back after the test
# ---------------------------------------------------------------------------
@pytest.fixture()
def db_session() -> Session:
    """
    Yields a session bound to a single connection with an open transaction.
    Everything is rolled back after the test — perfect isolation.
    """
    connection = _test_engine.connect()
    transaction = connection.begin()
    session = _TestingSessionLocal(bind=connection)

    yield session

    session.close()
    # Roll back to undo all inserts/updates from this test
    if transaction.is_active:
        transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# TestClient — shares the exact same Session as db_session
# ---------------------------------------------------------------------------
@pytest.fixture()
def client(db_session: Session):
    """
    Returns a FastAPI TestClient where get_db is overridden to yield
    the same db_session. Both the test body and the route handlers
    operate in the same transaction, so data seeded with db_session.flush()
    is immediately visible inside HTTP requests.
    """
    app = create_app()

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
