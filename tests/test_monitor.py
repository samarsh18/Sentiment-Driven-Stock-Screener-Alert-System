"""
tests/test_monitor.py
---------------------
Unit and integration tests for the StockMonitor background service.

Covers all 15 required specifications:
 1. monitor run_once processes watched stocks
 2. duplicate GDELT articles are skipped
 3. same article appearing in multiple users' watchlists is analyzed once
 4. users receive only alerts for their watchlisted stocks
 5. user notification preferences are respected
 6. failed GDELT call does not crash monitor
 7. failed AI pipeline for one article does not stop other articles
 8. failed notification does not delete alert
 9. same alert is not notified twice
10. poll interval is configurable
11. monitor can be started/stopped cleanly
12. monitor does not start when MONITOR_ENABLED=false
13. monitor handles empty watchlists
14. monitor handles no new articles
15. monitor handles one stock failing while other stocks succeed
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.database.models import (
    AlertRecord,
    Base,
    NewsRecord,
    NotificationDelivery,
    User,
    WatchlistItem,
)
from backend.app.database.repository import (
    add_watchlist_item,
    create_user,
    get_alerts_by_symbol,
)
from backend.app.main import create_app
from backend.app.models.news import NewsItem
from backend.app.notifications.base import NotificationProvider
from backend.app.notifications.service import NotificationService
from backend.app.providers.base import NewsProvider
from backend.app.services.monitor import MonitorCycleStats, StockMonitor
from backend.app.services.news_relevance import StockMetadata
from backend.app.services.pipeline import PipelineResult, StockNewsPipeline


class MockNewsProvider(NewsProvider):
    """Controllable in-memory news provider for tests."""

    def __init__(self, stock_news_map: Optional[Dict[str, List[NewsItem]]] = None):
        self.stock_news_map = stock_news_map or {}
        self.fetch_calls = []

    def fetch_news(self, symbol: str, company_name: str, limit: int = 20) -> list[NewsItem]:
        self.fetch_calls.append((symbol, company_name))
        return list(self.stock_news_map.get(symbol.upper(), []))


class MockNotificationProvider(NotificationProvider):
    """In-memory notification provider recording sent alerts."""

    def __init__(self, name: str = "mock_channel", fail: bool = False):
        self.name = name
        self.fail = fail
        self.delivered: List[tuple[str, str, Dict[str, Any]]] = []

    async def send(self, user_email: str, alert_id: str, context: Dict[str, Any]) -> None:
        if self.fail:
            raise RuntimeError(f"Channel {self.name} simulated delivery failure")
        self.delivered.append((user_email, alert_id, context))


def _make_news_item(news_id: str, symbol: str, company_name: str, title: str = "Quarterly results out") -> NewsItem:
    return NewsItem(
        news_id=news_id,
        symbol=symbol,
        company_name=company_name,
        title=title,
        content=f"Detailed financial update for {company_name}.",
        source="GDELT",
        url=f"https://news.example.com/{news_id}",
        published_at=datetime(2026, 5, 10, 8, 30, tzinfo=timezone.utc),
    )


@pytest.fixture
def test_db_factory():
    """Creates a fresh in-memory SQLite database session factory for each test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return TestingSession


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_1_run_once_processes_watched_stocks(test_db_factory):
    """1. monitor run_once processes watched stocks."""
    with test_db_factory() as db:
        user = create_user(db, "alice@example.com")
        add_watchlist_item(db, user.id, "RELIANCE", "Reliance Industries")

    item = _make_news_item("N-01", "RELIANCE", "Reliance Industries")
    provider = MockNewsProvider({"RELIANCE": [item]})
    notif_provider = MockNotificationProvider()
    notif_service = NotificationService(providers=[notif_provider])

    monitor = StockMonitor(
        session_factory=test_db_factory,
        news_provider=provider,
        notification_service=notif_service,
    )

    stats = await monitor.run_once()

    assert stats.stocks_monitored == 1
    assert stats.articles_fetched == 1
    assert stats.articles_analyzed == 1
    assert len(provider.fetch_calls) == 1
    assert provider.fetch_calls[0][0] == "RELIANCE"


@pytest.mark.asyncio
async def test_2_duplicate_gdelt_articles_skipped(test_db_factory):
    """2. duplicate GDELT articles are skipped (idempotency across cycles)."""
    with test_db_factory() as db:
        user = create_user(db, "bob@example.com")
        add_watchlist_item(db, user.id, "TCS", "Tata Consultancy")

    item = _make_news_item("N-DUP-01", "TCS", "Tata Consultancy")
    provider = MockNewsProvider({"TCS": [item]})
    notif_provider = MockNotificationProvider()
    notif_service = NotificationService(providers=[notif_provider])

    monitor = StockMonitor(
        session_factory=test_db_factory,
        news_provider=provider,
        notification_service=notif_service,
    )

    # First cycle -> article is new
    stats1 = await monitor.run_once()
    assert stats1.articles_unseen == 1
    assert stats1.articles_analyzed == 1

    # Second cycle with identical article -> skipped at DB layer
    stats2 = await monitor.run_once()
    assert stats2.articles_fetched == 1
    assert stats2.articles_unseen == 0  # Deduplicated!
    assert stats2.articles_analyzed == 0


@pytest.mark.asyncio
async def test_3_same_article_multiple_users_analyzed_once(test_db_factory):
    """3. same article appearing in multiple users' watchlists is analyzed once."""
    with test_db_factory() as db:
        u1 = create_user(db, "user1@example.com")
        u2 = create_user(db, "user2@example.com")
        add_watchlist_item(db, u1.id, "INFY", "Infosys Ltd")
        add_watchlist_item(db, u2.id, "INFY", "Infosys Ltd")

    item = _make_news_item("N-INFY-01", "INFY", "Infosys Ltd")
    provider = MockNewsProvider({"INFY": [item]})

    mock_pipeline = MagicMock(spec=StockNewsPipeline)
    mock_pipeline.process_news_item.return_value = PipelineResult(
        news_id="N-INFY-01",
        symbol="INFY",
        relevant=True,
        relevance_score=8,
        action="BUY",
        should_alert=True,
        reason="Positive earnings",
    )

    notif_provider = MockNotificationProvider()
    notif_service = NotificationService(providers=[notif_provider])

    monitor = StockMonitor(
        session_factory=test_db_factory,
        news_provider=provider,
        pipeline=mock_pipeline,
        notification_service=notif_service,
    )

    stats = await monitor.run_once()

    # Stock monitored once, pipeline executed once
    assert stats.stocks_monitored == 1
    assert mock_pipeline.process_news_item.call_count == 1
    # But both watching users should receive the notification
    assert len(notif_provider.delivered) == 2
    recipients = {d[0] for d in notif_provider.delivered}
    assert recipients == {"user1@example.com", "user2@example.com"}


@pytest.mark.asyncio
async def test_4_users_receive_only_alerts_for_their_stocks(test_db_factory):
    """4. users receive only alerts for their watchlisted stocks."""
    with test_db_factory() as db:
        u_apple = create_user(db, "apple_fan@example.com")
        u_tata = create_user(db, "tata_fan@example.com")
        add_watchlist_item(db, u_apple.id, "AAPL", "Apple Inc")
        add_watchlist_item(db, u_tata.id, "TCS", "Tata Consultancy")

    item_aapl = _make_news_item("N-AAPL", "AAPL", "Apple Inc", "Apple launches new M4 chip")
    item_tcs = _make_news_item("N-TCS", "TCS", "Tata Consultancy", "TCS wins mega cloud contract")

    provider = MockNewsProvider({
        "AAPL": [item_aapl],
        "TCS": [item_tcs],
    })

    mock_pipeline = MagicMock(spec=StockNewsPipeline)

    def _side_effect(item, metadata):
        return PipelineResult(
            news_id=item.news_id,
            symbol=item.symbol,
            relevant=True,
            relevance_score=10,
            action="BUY",
            should_alert=True,
            reason=f"Significant signal for {item.symbol}",
        )

    mock_pipeline.process_news_item.side_effect = _side_effect

    notif_provider = MockNotificationProvider()
    notif_service = NotificationService(providers=[notif_provider])

    monitor = StockMonitor(
        session_factory=test_db_factory,
        news_provider=provider,
        pipeline=mock_pipeline,
        notification_service=notif_service,
    )

    await monitor.run_once()

    apple_alerts = [d for d in notif_provider.delivered if d[0] == "apple_fan@example.com"]
    tata_alerts = [d for d in notif_provider.delivered if d[0] == "tata_fan@example.com"]

    assert len(apple_alerts) == 1
    assert apple_alerts[0][2]["symbol"] == "AAPL"

    assert len(tata_alerts) == 1
    assert tata_alerts[0][2]["symbol"] == "TCS"


@pytest.mark.asyncio
async def test_5_user_notification_preferences_respected(test_db_factory):
    """5. user notification preferences are respected (inactive users skipped)."""
    with test_db_factory() as db:
        active_user = create_user(db, "active@example.com", is_active=True)
        inactive_user = create_user(db, "inactive@example.com", is_active=False)
        add_watchlist_item(db, active_user.id, "SBIN", "State Bank of India")
        add_watchlist_item(db, inactive_user.id, "SBIN", "State Bank of India")

    item = _make_news_item("N-SBIN", "SBIN", "State Bank of India")
    provider = MockNewsProvider({"SBIN": [item]})

    mock_pipeline = MagicMock(spec=StockNewsPipeline)
    mock_pipeline.process_news_item.return_value = PipelineResult(
        news_id="N-SBIN",
        symbol="SBIN",
        relevant=True,
        relevance_score=8,
        action="BUY",
        should_alert=True,
        reason="Record quarterly net profit",
    )

    notif_provider = MockNotificationProvider()
    notif_service = NotificationService(providers=[notif_provider])

    monitor = StockMonitor(
        session_factory=test_db_factory,
        news_provider=provider,
        pipeline=mock_pipeline,
        notification_service=notif_service,
    )

    await monitor.run_once()

    # Only active user received notification
    assert len(notif_provider.delivered) == 1
    assert notif_provider.delivered[0][0] == "active@example.com"


@pytest.mark.asyncio
async def test_6_failed_gdelt_call_does_not_crash_monitor(test_db_factory):
    """6. failed GDELT call does not crash monitor."""
    with test_db_factory() as db:
        u = create_user(db, "user@example.com")
        add_watchlist_item(db, u.id, "CRASH_STOCK", "Failing Corp")

    failing_provider = MagicMock(spec=NewsProvider)
    failing_provider.fetch_news.side_effect = RuntimeError("GDELT HTTP 503 Service Unavailable")

    monitor = StockMonitor(
        session_factory=test_db_factory,
        news_provider=failing_provider,
    )

    stats = await monitor.run_once()
    assert stats.errors_count >= 1
    assert stats.stocks_monitored == 1
    assert stats.articles_fetched == 0


@pytest.mark.asyncio
async def test_7_failed_ai_pipeline_one_article_does_not_stop_others(test_db_factory):
    """7. failed AI pipeline for one article does not stop other articles."""
    with test_db_factory() as db:
        u = create_user(db, "user@example.com")
        add_watchlist_item(db, u.id, "WIPRO", "Wipro Limited")

    item1 = _make_news_item("N-BAD", "WIPRO", "Wipro Limited", "Faulty input")
    item2 = _make_news_item("N-GOOD", "WIPRO", "Wipro Limited", "Valid input")
    provider = MockNewsProvider({"WIPRO": [item1, item2]})

    mock_pipeline = MagicMock(spec=StockNewsPipeline)

    def _process_item(item, metadata):
        if item.news_id == "N-BAD":
            raise ValueError("Corrupt content")
        return PipelineResult(
            news_id=item.news_id,
            symbol=item.symbol,
            relevant=True,
            relevance_score=7,
            action="BUY",
            should_alert=True,
            reason="Good signal",
        )

    mock_pipeline.process_news_item.side_effect = _process_item

    notif_provider = MockNotificationProvider()
    notif_service = NotificationService(providers=[notif_provider])

    monitor = StockMonitor(
        session_factory=test_db_factory,
        news_provider=provider,
        pipeline=mock_pipeline,
        notification_service=notif_service,
    )

    stats = await monitor.run_once()
    assert stats.articles_fetched == 2
    assert stats.articles_analyzed == 1  # 1 analyzed, 1 failed
    assert stats.alerts_generated == 1
    assert stats.errors_count >= 1


@pytest.mark.asyncio
async def test_8_failed_notification_does_not_delete_alert(test_db_factory):
    """8. failed notification does not delete alert."""
    with test_db_factory() as db:
        u = create_user(db, "user@example.com")
        add_watchlist_item(db, u.id, "HDFC", "HDFC Bank")

    item = _make_news_item("N-HDFC", "HDFC", "HDFC Bank")
    provider = MockNewsProvider({"HDFC": [item]})

    mock_pipeline = MagicMock(spec=StockNewsPipeline)
    mock_pipeline.process_news_item.return_value = PipelineResult(
        news_id="N-HDFC",
        symbol="HDFC",
        relevant=True,
        relevance_score=9,
        action="BUY",
        should_alert=True,
        reason="Merger synergies",
    )

    failing_notif = MockNotificationProvider(fail=True)
    notif_service = NotificationService(providers=[failing_notif])

    monitor = StockMonitor(
        session_factory=test_db_factory,
        news_provider=provider,
        pipeline=mock_pipeline,
        notification_service=notif_service,
    )

    await monitor.run_once()

    # Verify AlertRecord STILL EXISTS in database
    with test_db_factory() as db:
        alerts = get_alerts_by_symbol(db, "HDFC")
        assert len(alerts) == 1
        assert alerts[0].alert_id == "ALERT-N-HDFC"

        # Verify failure recorded in NotificationDelivery
        deliv = db.query(NotificationDelivery).filter_by(alert_id="ALERT-N-HDFC").first()
        assert deliv is not None
        assert deliv.status == "failed"


@pytest.mark.asyncio
async def test_9_same_alert_not_notified_twice(test_db_factory):
    """9. same alert is not notified twice."""
    with test_db_factory() as db:
        u = create_user(db, "user@example.com")
        add_watchlist_item(db, u.id, "ITC", "ITC Ltd")

    item = _make_news_item("N-ITC", "ITC", "ITC Ltd")
    provider = MockNewsProvider({"ITC": [item]})

    mock_pipeline = MagicMock(spec=StockNewsPipeline)
    mock_pipeline.process_news_item.return_value = PipelineResult(
        news_id="N-ITC",
        symbol="ITC",
        relevant=True,
        relevance_score=8,
        action="BUY",
        should_alert=True,
        reason="Hotel business demerger",
    )

    notif_provider = MockNotificationProvider()
    notif_service = NotificationService(providers=[notif_provider])

    monitor = StockMonitor(
        session_factory=test_db_factory,
        news_provider=provider,
        pipeline=mock_pipeline,
        notification_service=notif_service,
    )

    # Cycle 1 -> alert created and delivered
    stats1 = await monitor.run_once()
    assert stats1.notifications_sent == 1
    assert len(notif_provider.delivered) == 1

    # Cycle 2 -> provider returns same item, DB skips it, no notification
    stats2 = await monitor.run_once()
    assert stats2.notifications_sent == 0
    assert len(notif_provider.delivered) == 1


def test_10_poll_interval_is_configurable():
    """10. poll interval is configurable via constructor and env var."""
    # From constructor
    m1 = StockMonitor(poll_interval_seconds=45)
    assert m1.poll_interval_seconds == 45

    # From env var
    with patch.dict(os.environ, {"MONITOR_POLL_INTERVAL_SECONDS": "120"}):
        m2 = StockMonitor()
        assert m2.poll_interval_seconds == 120

    # Fallback on invalid env var
    with patch.dict(os.environ, {"MONITOR_POLL_INTERVAL_SECONDS": "not_an_int"}):
        m3 = StockMonitor()
        assert m3.poll_interval_seconds == 300


@pytest.mark.asyncio
async def test_11_monitor_can_be_started_and_stopped_cleanly():
    """11. monitor can be started/stopped cleanly without orphaned tasks."""
    monitor = StockMonitor(poll_interval_seconds=1)

    # Mock run_once to prevent DB operations
    monitor.run_once = AsyncMock(return_value=MonitorCycleStats(started_at=datetime.now(timezone.utc)))

    task = monitor.start()
    assert monitor.is_running is True
    assert not task.done()

    # Calling start again should return the existing task
    task2 = monitor.start()
    assert task2 == task

    await asyncio.sleep(0.05)
    await monitor.stop()

    assert monitor.is_running is False
    assert task.done()


def test_12_monitor_does_not_start_when_disabled():
    """12. monitor does not start when MONITOR_ENABLED=false."""
    with patch.dict(os.environ, {"MONITOR_ENABLED": "false"}):
        app = create_app()
        with TestClient(app) as client:
            resp = client.get("/api/monitor/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["enabled"] is False
            assert data["running"] is False


@pytest.mark.asyncio
async def test_13_handles_empty_watchlists(test_db_factory):
    """13. monitor handles empty watchlists without errors."""
    with test_db_factory() as db:
        create_user(db, "lonely@example.com")  # No watchlist items

    provider = MockNewsProvider()
    monitor = StockMonitor(
        session_factory=test_db_factory,
        news_provider=provider,
    )

    stats = await monitor.run_once()
    assert stats.stocks_monitored == 0
    assert stats.articles_fetched == 0
    assert stats.errors_count == 0


@pytest.mark.asyncio
async def test_14_handles_no_new_articles(test_db_factory):
    """14. monitor handles no new articles gracefully."""
    with test_db_factory() as db:
        u = create_user(db, "investor@example.com")
        add_watchlist_item(db, u.id, "QUIET_STOCK", "Quiet Industries")

    # Provider returns empty list
    provider = MockNewsProvider({"QUIET_STOCK": []})
    monitor = StockMonitor(
        session_factory=test_db_factory,
        news_provider=provider,
    )

    stats = await monitor.run_once()
    assert stats.stocks_monitored == 1
    assert stats.articles_fetched == 0
    assert stats.articles_analyzed == 0
    assert stats.alerts_generated == 0
    assert stats.errors_count == 0


@pytest.mark.asyncio
async def test_15_one_stock_failing_while_other_succeeds(test_db_factory):
    """15. monitor handles one stock failing while other stocks succeed."""
    with test_db_factory() as db:
        u = create_user(db, "diversified@example.com")
        add_watchlist_item(db, u.id, "STOCK_A", "Alpha Corp")
        add_watchlist_item(db, u.id, "STOCK_B", "Beta Corp")

    item_b = _make_news_item("N-B", "STOCK_B", "Beta Corp")

    class SelectiveFailingProvider(NewsProvider):
        def fetch_news(self, symbol: str, company_name: str, limit: int = 20) -> list[NewsItem]:
            if symbol.upper() == "STOCK_A":
                raise ConnectionError("Timeout fetching STOCK_A news")
            return [item_b]

    mock_pipeline = MagicMock(spec=StockNewsPipeline)
    mock_pipeline.process_news_item.return_value = PipelineResult(
        news_id="N-B",
        symbol="STOCK_B",
        relevant=True,
        relevance_score=8,
        action="BUY",
        should_alert=True,
        reason="Solid performance",
    )

    notif_provider = MockNotificationProvider()
    notif_service = NotificationService(providers=[notif_provider])

    monitor = StockMonitor(
        session_factory=test_db_factory,
        news_provider=SelectiveFailingProvider(),
        pipeline=mock_pipeline,
        notification_service=notif_service,
    )

    stats = await monitor.run_once()
    assert stats.stocks_monitored == 2
    assert stats.articles_analyzed == 1
    assert stats.alerts_generated == 1
    assert stats.errors_count >= 1
    assert len(notif_provider.delivered) == 1
    assert notif_provider.delivered[0][2]["symbol"] == "STOCK_B"
