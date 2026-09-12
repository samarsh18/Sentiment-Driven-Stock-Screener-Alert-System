"""
tests/api/test_integration_validation.py
-------------------------------------------
Backend Integration Validation Tests for background monitor and frontend compatibility.

Verifies:
1. End-to-end flow: User -> Watchlist -> News Ingestion -> Alert Generation -> REST API consumption.
2. Market Data: Market data persistence -> REST API history endpoint consumption.
3. Severity mapping compatibility: DB integer severity <-> API integer + string label.
4. Monitoring worker helper compatibility (watchlist and user preferences queries).
"""
from datetime import datetime, timezone

from backend.app.database.models import User
from backend.app.database.repository import (
    add_watchlist_item,
    create_alert,
    create_user,
    get_user_by_id,
    get_user_watchlist,
    save_market_data,
    save_news_items,
)
from backend.app.models.market import MarketDataBar
from backend.app.models.news import NewsItem


def test_full_pipeline_to_api_integration_flow(client, db_session):
    """
    End-to-end integration test:
    1. Create user via API / repo
    2. Add stock to watchlist
    3. Simulate monitoring worker ingesting NewsRecord
    4. Simulate pipeline generating & persisting AlertRecord
    5. Verify GET /api/users/{user_id}/alerts returns the alert
    6. Verify GET /api/users/{user_id}/news returns the news
    7. Verify GET /api/stocks/{symbol}/news returns the news
    8. Verify GET /api/news/{news_id} returns the specific news item
    9. Verify worker can retrieve user preferences and watchlist
    """
    # 1. Create user via API
    res_user = client.post("/api/users", json={"email": "integration_user@example.com"})
    assert res_user.status_code == 201
    user_data = res_user.json()
    user_id = user_data["id"]

    # 2. Add stock to watchlist via API
    res_wl = client.post(
        f"/api/users/{user_id}/watchlist",
        json={"symbol": "RELIANCE", "company_name": "Reliance Industries Ltd"},
    )
    assert res_wl.status_code == 201

    # 3. Simulate background monitoring worker fetching news and persisting via repository
    news_item = NewsItem(
        news_id="REL-2024-001",
        symbol="RELIANCE",
        company_name="Reliance Industries Ltd",
        title="Reliance announces major green energy initiative",
        content="Reliance Industries announced a massive $10B investment in solar and hydrogen infrastructure.",
        source="Reuters",
        url="https://example.com/reliance-green",
        published_at=datetime(2024, 5, 10, 10, 0, 0, tzinfo=timezone.utc),
    )
    saved_news = save_news_items(db_session, [news_item])
    assert len(saved_news) == 1
    db_session.flush()

    # 4. Simulate pipeline/decision engine producing and persisting an alert
    created_alert = create_alert(
        db=db_session,
        alert_id="ALERT-REL-001",
        symbol="RELIANCE",
        action="OPPORTUNITY",
        severity=8,
        message="High-impact positive ESG news detected for RELIANCE.",
        user_id=user_id,
        should_alert=True,
    )
    assert created_alert.id is not None
    db_session.flush()

    # 5. Verify GET /api/users/{user_id}/alerts
    res_alerts = client.get(f"/api/users/{user_id}/alerts")
    assert res_alerts.status_code == 200
    alerts_data = res_alerts.json()
    assert alerts_data["pagination"]["total"] == 1
    alert_item = alerts_data["items"][0]
    assert alert_item["alert_id"] == "ALERT-REL-001"
    assert alert_item["symbol"] == "RELIANCE"
    assert alert_item["action"] == "OPPORTUNITY"
    assert alert_item["severity"] == 8
    assert alert_item["severity_label"] == "HIGH"
    assert alert_item["user_id"] == user_id

    # 6. Verify GET /api/users/{user_id}/news (user's watchlist news feed)
    res_user_news = client.get(f"/api/users/{user_id}/news")
    assert res_user_news.status_code == 200
    user_news_data = res_user_news.json()
    assert user_news_data["pagination"]["total"] == 1
    assert user_news_data["items"][0]["news_id"] == "REL-2024-001"

    # 7. Verify GET /api/stocks/{symbol}/news
    res_stock_news = client.get("/api/stocks/RELIANCE/news")
    assert res_stock_news.status_code == 200
    stock_news_data = res_stock_news.json()
    assert stock_news_data["pagination"]["total"] == 1
    assert stock_news_data["items"][0]["title"] == "Reliance announces major green energy initiative"

    # 8. Verify GET /api/news/{news_id}
    res_single_news = client.get("/api/news/REL-2024-001")
    assert res_single_news.status_code == 200
    assert res_single_news.json()["news_id"] == "REL-2024-001"

    # 9. Verify worker helper compatibility: reading user preferences & watchlist directly
    user_orm = get_user_by_id(db_session, user_id)
    assert user_orm is not None
    assert user_orm.is_active is True

    user_watchlist = get_user_watchlist(db_session, user_id)
    assert len(user_watchlist) == 1
    assert user_watchlist[0].symbol == "RELIANCE"


def test_historical_prices_integration_flow(client, db_session):
    """
    Historical prices integration test:
    1. Persist market OHLCV bars via repository save_market_data()
    2. GET /api/stocks/{symbol}/history
    3. Verify OHLCV response structure, normalization, and values
    """
    bars = [
        MarketDataBar(
            symbol="INFY",
            exchange="NSE",
            timestamp=datetime(2024, 6, 1, 9, 15, tzinfo=timezone.utc),
            open=1400.0,
            high=1425.0,
            low=1395.0,
            close=1420.0,
            volume=1500000.0,
        ),
        MarketDataBar(
            symbol="INFY",
            exchange="NSE",
            timestamp=datetime(2024, 6, 2, 9, 15, tzinfo=timezone.utc),
            open=1420.0,
            high=1440.0,
            low=1415.0,
            close=1435.0,
            volume=1800000.0,
        ),
    ]
    saved_count = save_market_data(db_session, bars)
    assert saved_count == 2
    db_session.flush()

    res_history = client.get("/api/stocks/INFY/history?exchange=NSE")
    assert res_history.status_code == 200
    history_data = res_history.json()

    assert history_data["symbol"] == "INFY"
    assert history_data["exchange"] == "NSE"
    assert history_data["total"] == 2

    item0 = history_data["items"][0]
    assert item0["symbol"] == "INFY"
    assert item0["open"] == 1400.0
    assert item0["high"] == 1425.0
    assert item0["low"] == 1395.0
    assert item0["close"] == 1420.0
    assert item0["volume"] == 1500000.0

    item1 = history_data["items"][1]
    assert item1["close"] == 1435.0


def test_severity_representation_compatibility(client, db_session):
    """
    Compatibility test for severity representation:
    1. Persist alert records with integer severities (1 through 10)
    2. GET /api/users/{user_id}/alerts
    3. Verify every response object contains integer severity AND corresponding string severity_label.
    """
    user = create_user(db_session, email="severity_compat@example.com")
    db_session.flush()

    test_cases = [
        (1, "LOW"),
        (3, "LOW"),
        (4, "MEDIUM"),
        (6, "MEDIUM"),
        (7, "HIGH"),
        (9, "HIGH"),
        (10, "HIGH"),
    ]

    for idx, (sev_int, expected_label) in enumerate(test_cases):
        create_alert(
            db=db_session,
            alert_id=f"SEV-TEST-{idx:03d}",
            symbol="TCS",
            action="WATCH",
            severity=sev_int,
            message=f"Test severity {sev_int}",
            user_id=user.id,
            should_alert=True,
        )
    db_session.flush()

    res = client.get(f"/api/users/{user.id}/alerts?limit=50")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == len(test_cases)

    # Build map of severity int -> severity label from API response
    api_map = {item["severity"]: item["severity_label"] for item in items}

    for sev_int, expected_label in test_cases:
        assert sev_int in api_map
        assert api_map[sev_int] == expected_label, (
            f"Expected severity {sev_int} to map to {expected_label}, got {api_map[sev_int]}"
        )
