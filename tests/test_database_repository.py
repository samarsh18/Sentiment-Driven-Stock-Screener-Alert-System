"""
tests/test_database_repository.py
----------------------------------
Unit tests for backend.app.database.repository and init_db.

Uses an in-memory SQLite database so tests are 100% offline and isolated.
"""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database.config import init_db
from backend.app.database.models import AlertRecord, Base, NewsRecord, User, WatchlistItem
from backend.app.database.repository import (
    add_watchlist_item,
    create_alert,
    create_user,
    get_alerts_by_symbol,
    get_alerts_by_user,
    get_news_by_symbol,
    get_user_watchlist,
    remove_watchlist_item,
    save_news_items,
)
from backend.app.models.news import NewsItem


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    init_db(target_engine=engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


class TestDatabaseInit:
    def test_init_db_creates_tables(self):
        engine = create_engine("sqlite:///:memory:")
        init_db(target_engine=engine)
        inspector = pytest.importorskip("sqlalchemy").inspect(engine)
        tables = inspector.get_table_names()
        assert "users" in tables
        assert "watchlist_items" in tables
        assert "news_records" in tables
        assert "alert_records" in tables

    def test_calling_init_db_twice_is_safe(self):
        engine = create_engine("sqlite:///:memory:")
        init_db(target_engine=engine)
        init_db(target_engine=engine)
        inspector = pytest.importorskip("sqlalchemy").inspect(engine)
        assert "users" in inspector.get_table_names()


class TestNewsRepository:
    def test_save_one_news_item(self, db_session):
        now = datetime.now(timezone.utc)
        item = NewsItem(
            news_id="NEWS-001",
            symbol="AAPL",
            company_name="Apple Inc.",
            title="Apple Q3 Beat",
            content="Apple reported stellar Q3 earnings...",
            source="Reuters",
            url="https://reuters.example.com/aapl-q3",
            published_at=now,
        )

        persisted = save_news_items(db_session, [item])
        assert len(persisted) == 1
        assert persisted[0].news_id == "NEWS-001"
        assert persisted[0].symbol == "AAPL"

    def test_retrieve_news_by_symbol(self, db_session):
        now = datetime.now(timezone.utc)
        item1 = NewsItem(
            news_id="N-1",
            symbol="MSFT",
            company_name="Microsoft",
            title="MSFT Cloud Growth",
            content="Azure revenue grew 30%...",
            source="Bloomberg",
            url="https://example.com/msft1",
            published_at=now,
        )
        save_news_items(db_session, [item1])

        records = get_news_by_symbol(db_session, "MSFT")
        assert len(records) == 1
        assert records[0].title == "MSFT Cloud Growth"

    def test_uppercase_symbol_behavior(self, db_session):
        now = datetime.now(timezone.utc)
        item = NewsItem(
            news_id="N-UP",
            symbol="nvda",
            company_name="NVIDIA",
            title="Nvidia GPUs Surge",
            content="Demand for Blackwell GPUs...",
            source="TechCrunch",
            url="https://example.com/nvda",
            published_at=now,
        )
        save_news_items(db_session, [item])

        records = get_news_by_symbol(db_session, "nvda")
        assert len(records) == 1
        assert records[0].symbol == "NVDA"

    def test_limit_behavior(self, db_session):
        now = datetime.now(timezone.utc)
        items = [
            NewsItem(
                news_id=f"LIMIT-{i}",
                symbol="GOOGL",
                company_name="Alphabet",
                title=f"Title {i}",
                content=f"Content {i}",
                source="NewsWire",
                url=f"https://example.com/googl/{i}",
                published_at=now - timedelta(hours=i),
            )
            for i in range(10)
        ]
        save_news_items(db_session, items)

        records = get_news_by_symbol(db_session, "GOOGL", limit=3)
        assert len(records) == 3

    def test_duplicate_news_id_does_not_create_duplicate_rows(self, db_session):
        now = datetime.now(timezone.utc)
        item = NewsItem(
            news_id="DUP-001",
            symbol="TSLA",
            company_name="Tesla",
            title="Tesla Robotaxi Event",
            content="Tesla held robotaxi unveiling...",
            source="Electrek",
            url="https://example.com/tesla-rt",
            published_at=now,
        )

        res1 = save_news_items(db_session, [item])
        res2 = save_news_items(db_session, [item])

        assert len(res1) == 1
        assert len(res2) == 0

        all_records = get_news_by_symbol(db_session, "TSLA")
        assert len(all_records) == 1

    def test_ordering_by_published_at(self, db_session):
        base_time = datetime(2024, 4, 25, 12, 0, 0, tzinfo=timezone.utc)
        item_old = NewsItem(
            news_id="OLD",
            symbol="AMZN",
            company_name="Amazon",
            title="Old News",
            content="Older content...",
            source="WSJ",
            url="https://example.com/amzn-old",
            published_at=base_time - timedelta(days=2),
        )
        item_new = NewsItem(
            news_id="NEW",
            symbol="AMZN",
            company_name="Amazon",
            title="New News",
            content="Newer content...",
            source="WSJ",
            url="https://example.com/amzn-new",
            published_at=base_time,
        )

        save_news_items(db_session, [item_old, item_new])

        records = get_news_by_symbol(db_session, "AMZN")
        assert len(records) == 2
        assert records[0].news_id == "NEW"
        assert records[1].news_id == "OLD"


class TestWatchlistRepository:
    def test_create_user(self, db_session):
        user = create_user(db_session, "Trader@Example.com")
        assert user.id is not None
        assert user.email == "trader@example.com"

        dup = create_user(db_session, "trader@example.com")
        assert dup.id == user.id

    def test_add_and_retrieve_watchlist_item(self, db_session):
        user = create_user(db_session, "user1@example.com")
        item = add_watchlist_item(db_session, user.id, "aapl", "Apple Inc.")

        assert item.id is not None
        assert item.symbol == "AAPL"
        assert item.company_name == "Apple Inc."

        watchlist = get_user_watchlist(db_session, user.id)
        assert len(watchlist) == 1
        assert watchlist[0].symbol == "AAPL"

    def test_duplicate_watchlist_item(self, db_session):
        user = create_user(db_session, "user2@example.com")
        item1 = add_watchlist_item(db_session, user.id, "MSFT", "Microsoft")
        item2 = add_watchlist_item(db_session, user.id, "msft", "Microsoft")

        assert item1.id == item2.id
        watchlist = get_user_watchlist(db_session, user.id)
        assert len(watchlist) == 1

    def test_remove_watchlist_item(self, db_session):
        user = create_user(db_session, "user3@example.com")
        add_watchlist_item(db_session, user.id, "NVDA", "Nvidia")

        removed = remove_watchlist_item(db_session, user.id, "nvda")
        assert removed is True
        assert len(get_user_watchlist(db_session, user.id)) == 0

    def test_remove_missing_item_safely(self, db_session):
        user = create_user(db_session, "user4@example.com")
        removed = remove_watchlist_item(db_session, user.id, "NONEXISTENT")
        assert removed is False


class TestAlertRepository:
    def test_create_and_persist_alert(self, db_session):
        user = create_user(db_session, "alert_user@example.com")
        alert = create_alert(
            db=db_session,
            alert_id="ALT-1001",
            symbol="aapl",
            action="RISK_ALERT",
            severity=9,
            message="Risk alert for AAPL: Revenue miss guidance",
            user_id=user.id,
            should_alert=True,
        )

        assert alert.id is not None
        assert alert.alert_id == "ALT-1001"
        assert alert.symbol == "AAPL"
        assert alert.action == "RISK_ALERT"
        assert alert.severity == 9

    def test_retrieve_alerts_by_user_and_symbol(self, db_session):
        user = create_user(db_session, "alert_user2@example.com")
        create_alert(
            db=db_session,
            alert_id="ALT-1002",
            symbol="TSLA",
            action="OPPORTUNITY",
            severity=8,
            message="Opportunity signal for TSLA",
            user_id=user.id,
        )

        user_alerts = get_alerts_by_user(db_session, user.id)
        assert len(user_alerts) == 1
        assert user_alerts[0].alert_id == "ALT-1002"

        symbol_alerts = get_alerts_by_symbol(db_session, "tsla")
        assert len(symbol_alerts) == 1
        assert symbol_alerts[0].action == "OPPORTUNITY"

    def test_duplicate_alert_id_does_not_create_duplicate(self, db_session):
        alert1 = create_alert(
            db=db_session,
            alert_id="ALT-DUP",
            symbol="AMD",
            action="WATCH",
            severity=5,
            message="Watch AMD",
        )
        alert2 = create_alert(
            db=db_session,
            alert_id="ALT-DUP",
            symbol="AMD",
            action="WATCH",
            severity=5,
            message="Watch AMD",
        )

        assert alert1.id == alert2.id
        alerts = get_alerts_by_symbol(db_session, "AMD")
        assert len(alerts) == 1