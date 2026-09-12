"""
tests/test_database.py
-----------------------
Tests for Person 2's database layer.

Coverage:
  1.  All three tables are created when create_all() is called.
  2.  User can be created and queried.
  3.  User email must be unique (IntegrityError on duplicate).
  4.  WatchlistItem can be created linked to a User.
  5.  (user_id, symbol) must be unique on watchlist_items.
  6.  Deleting a User cascades to WatchlistItems.
  7.  NewsRecord can be created and queried.
  8.  NewsRecord.news_id is unique (deduplication enforcement).
  9.  Multiple NewsRecords for the same symbol are allowed.
  10. Basic update: User.is_active can be toggled.
  11. Basic delete: WatchlistItem can be deleted independently.
  12. Session lifecycle — session closes cleanly via get_db().
  13. SQLite engine connects without error.
  14. DATABASE_URL defaults to SQLite when env var is absent.
  15. NewsRecord fields mirror the NewsItem contract field names.
"""

import os
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Use an isolated in-memory SQLite DB for every test session.
# This keeps tests fast and leaves no files on disk.
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite:///:memory:"

from backend.app.database.models import Base, NewsRecord, User, WatchlistItem


@pytest.fixture(scope="module")
def engine():
    """Create an in-memory SQLite engine shared across all tests in this module."""
    eng = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture()
def db(engine):
    """
    Provide a transactionally-isolated session for each test.

    SQLAlchemy 2.x pattern:
    - The outer connection begins a transaction that wraps the whole test.
    - Each test runs inside a SAVEPOINT.
    - On teardown the SAVEPOINT is released/rolled back, then the outer
      transaction is rolled back — leaving the DB in its original state.

    This correctly handles tests that trigger an IntegrityError: the error
    breaks only the inner SAVEPOINT, not the outer transaction, so rollback
    can always proceed without SAWarnings.
    """
    connection = engine.connect()
    trans = connection.begin()          # outer transaction
    Session = sessionmaker(bind=connection)
    session = Session()
    # Begin a nested (SAVEPOINT) transaction for this single test
    session.begin_nested()

    yield session

    # Always roll back to the SAVEPOINT, then the outer transaction
    session.rollback()
    session.close()
    trans.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(email: str = "alice@example.com") -> User:
    return User(email=email)


def make_watchlist(user: User, symbol: str = "AAPL") -> WatchlistItem:
    return WatchlistItem(
        user=user,
        symbol=symbol,
        company_name="Apple Inc.",
    )


def make_news(
    news_id: str = "AAPL-q-beat-001",
    symbol: str = "AAPL",
) -> NewsRecord:
    return NewsRecord(
        news_id=news_id,
        symbol=symbol,
        company_name="Apple Inc.",
        title="Apple beats quarterly earnings expectations",
        content="Apple reported strong Q2 results, beating estimates.",
        source="MockFinancialTimes",
        url="https://mock-news.example.com/AAPL/earnings-beat",
        published_at=datetime(2024, 4, 25, 13, 30, 0, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# 1. Table creation
# ---------------------------------------------------------------------------

class TestTableCreation:
    def test_all_tables_exist(self, engine):
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "users" in tables
        assert "watchlist_items" in tables
        assert "news_records" in tables

    def test_engine_connects(self, engine):
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1


# ---------------------------------------------------------------------------
# 2. User — create & query
# ---------------------------------------------------------------------------

class TestUserModel:
    def test_create_user(self, db):
        user = make_user()
        db.add(user)
        db.flush()
        assert user.id is not None
        assert user.email == "alice@example.com"
        assert user.is_active is True

    def test_query_user(self, db):
        user = make_user("bob@example.com")
        db.add(user)
        db.flush()
        found = db.query(User).filter_by(email="bob@example.com").first()
        assert found is not None
        assert found.email == "bob@example.com"

    def test_user_repr(self, db):
        user = make_user("repr@example.com")
        db.add(user)
        db.flush()
        assert "repr@example.com" in repr(user)

    def test_user_is_active_default(self, db):
        user = make_user("active@example.com")
        db.add(user)
        db.flush()
        assert user.is_active is True


# ---------------------------------------------------------------------------
# 3. User email uniqueness
# ---------------------------------------------------------------------------

class TestUserUniqueness:
    def test_duplicate_email_raises(self, db):
        db.add(make_user("dup@example.com"))
        db.flush()
        db.add(make_user("dup@example.com"))
        with pytest.raises(IntegrityError):
            db.flush()


# ---------------------------------------------------------------------------
# 4. WatchlistItem — create linked to User
# ---------------------------------------------------------------------------

class TestWatchlistItemModel:
    def test_create_watchlist_item(self, db):
        user = make_user("watchlist@example.com")
        db.add(user)
        db.flush()
        item = make_watchlist(user, "AAPL")
        db.add(item)
        db.flush()
        assert item.id is not None
        assert item.symbol == "AAPL"
        assert item.company_name == "Apple Inc."
        assert item.user_id == user.id

    def test_user_has_watchlist_items(self, db):
        user = make_user("multi@example.com")
        db.add(user)
        db.flush()
        for symbol, name in [("AAPL", "Apple Inc."), ("MSFT", "Microsoft")]:
            db.add(WatchlistItem(user=user, symbol=symbol, company_name=name))
        db.flush()
        assert len(user.watchlist_items) == 2

    def test_watchlist_repr(self, db):
        user = make_user("wrepr@example.com")
        db.add(user)
        db.flush()
        item = make_watchlist(user, "TSLA")
        db.add(item)
        db.flush()
        assert "TSLA" in repr(item)


# ---------------------------------------------------------------------------
# 5. WatchlistItem uniqueness per user
# ---------------------------------------------------------------------------

class TestWatchlistUniqueness:
    def test_duplicate_symbol_per_user_raises(self, db):
        user = make_user("uquser@example.com")
        db.add(user)
        db.flush()
        db.add(make_watchlist(user, "NVDA"))
        db.flush()
        db.add(make_watchlist(user, "NVDA"))
        with pytest.raises(IntegrityError):
            db.flush()

    def test_same_symbol_different_users_allowed(self, db):
        u1 = make_user("u1@example.com")
        u2 = make_user("u2@example.com")
        db.add_all([u1, u2])
        db.flush()
        db.add(WatchlistItem(user=u1, symbol="GOOGL", company_name="Alphabet"))
        db.add(WatchlistItem(user=u2, symbol="GOOGL", company_name="Alphabet"))
        db.flush()  # Should not raise


# ---------------------------------------------------------------------------
# 6. Cascade delete
# ---------------------------------------------------------------------------

class TestCascadeDelete:
    def test_delete_user_cascades_to_watchlist(self, db):
        user = make_user("cascade@example.com")
        db.add(user)
        db.flush()
        db.add(make_watchlist(user, "AMZN"))
        db.flush()
        user_id = user.id

        db.delete(user)
        db.flush()

        remaining = db.query(WatchlistItem).filter_by(user_id=user_id).all()
        assert remaining == []


# ---------------------------------------------------------------------------
# 7. NewsRecord — create & query
# ---------------------------------------------------------------------------

class TestNewsRecordModel:
    def test_create_news_record(self, db):
        record = make_news()
        db.add(record)
        db.flush()
        assert record.id is not None
        assert record.symbol == "AAPL"
        assert record.news_id == "AAPL-q-beat-001"

    def test_query_by_symbol(self, db):
        db.add(make_news("AAPL-001", "AAPL"))
        db.add(make_news("MSFT-001", "MSFT"))
        db.flush()
        aapl_records = db.query(NewsRecord).filter_by(symbol="AAPL").all()
        assert all(r.symbol == "AAPL" for r in aapl_records)

    def test_news_record_repr(self, db):
        record = make_news("repr-001", "AAPL")
        db.add(record)
        db.flush()
        r = repr(record)
        assert "AAPL" in r
        assert "repr-001" in r

    def test_news_record_has_published_at(self, db):
        record = make_news("dt-001", "AAPL")
        db.add(record)
        db.flush()
        assert isinstance(record.published_at, datetime)


# ---------------------------------------------------------------------------
# 8. NewsRecord deduplication via unique news_id
# ---------------------------------------------------------------------------

class TestNewsRecordDeduplication:
    def test_duplicate_news_id_raises(self, db):
        db.add(make_news("DUP-001", "AAPL"))
        db.flush()
        db.add(make_news("DUP-001", "AAPL"))
        with pytest.raises(IntegrityError):
            db.flush()


# ---------------------------------------------------------------------------
# 9. Multiple records per symbol
# ---------------------------------------------------------------------------

class TestMultipleNewsRecords:
    def test_multiple_records_same_symbol(self, db):
        for i in range(3):
            db.add(make_news(f"AAPL-multi-{i:03}", "AAPL"))
        db.flush()
        records = db.query(NewsRecord).filter_by(symbol="AAPL").all()
        assert len(records) == 3


# ---------------------------------------------------------------------------
# 10. Update
# ---------------------------------------------------------------------------

class TestUpdate:
    def test_toggle_user_is_active(self, db):
        user = make_user("toggle@example.com")
        db.add(user)
        db.flush()
        assert user.is_active is True
        user.is_active = False
        db.flush()
        refreshed = db.query(User).filter_by(email="toggle@example.com").first()
        assert refreshed.is_active is False


# ---------------------------------------------------------------------------
# 11. Delete WatchlistItem independently
# ---------------------------------------------------------------------------

class TestIndependentDelete:
    def test_delete_watchlist_item_leaves_user(self, db):
        user = make_user("nodelete@example.com")
        db.add(user)
        db.flush()
        item = make_watchlist(user, "META")
        db.add(item)
        db.flush()
        item_id = item.id

        db.delete(item)
        db.flush()

        still_there = db.query(User).filter_by(email="nodelete@example.com").first()
        assert still_there is not None
        gone = db.query(WatchlistItem).filter_by(id=item_id).first()
        assert gone is None


# ---------------------------------------------------------------------------
# 12. Session lifecycle via get_db()
# ---------------------------------------------------------------------------

class TestSessionLifecycle:
    def test_get_db_yields_and_closes(self):
        from backend.app.database.config import get_db
        gen = get_db()
        session = next(gen)
        assert session is not None
        # Exhaust the generator to trigger the finally block (close)
        try:
            next(gen)
        except StopIteration:
            pass  # Expected — generator is exhausted after yield


# ---------------------------------------------------------------------------
# 13 & 14. Config module
# ---------------------------------------------------------------------------

class TestDatabaseConfig:
    def test_default_database_url_is_sqlite(self):
        """When DATABASE_URL is not set the default must be SQLite."""
        saved = os.environ.pop("DATABASE_URL", None)
        try:
            import importlib
            import backend.app.database.config as cfg
            importlib.reload(cfg)
            assert "sqlite" in cfg.DATABASE_URL
        finally:
            if saved is not None:
                os.environ["DATABASE_URL"] = saved
            import importlib
            import backend.app.database.config as cfg
            importlib.reload(cfg)

    def test_session_local_is_callable(self):
        from backend.app.database.config import SessionLocal
        assert callable(SessionLocal)


# ---------------------------------------------------------------------------
# 15. Field name alignment with NewsItem contract
# ---------------------------------------------------------------------------

class TestNewsRecordFieldAlignment:
    """
    Verify that NewsRecord column names match the Pydantic NewsItem contract
    from docs/PROJECT_CONTEXT.md so Person 2 and Person 1 stay in sync.
    """
    EXPECTED_FIELDS = [
        "news_id", "symbol", "company_name",
        "title", "content", "source", "url", "published_at",
    ]

    def test_all_contract_fields_present(self, engine):
        inspector = inspect(engine)
        cols = {c["name"] for c in inspector.get_columns("news_records")}
        for field in self.EXPECTED_FIELDS:
            assert field in cols, f"Column '{field}' missing from news_records table"
