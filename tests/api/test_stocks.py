"""
tests/api/test_stocks.py
--------------------------
Tests for Stocks API endpoints.

GET /api/stocks/{symbol}/history
"""
from datetime import datetime, timezone

from backend.app.database.models import HistoricalPrice


def _seed_prices(db_session, symbol="TCS", exchange="NSE", count=5):
    for i in range(count):
        r = HistoricalPrice(
            symbol=symbol,
            exchange=exchange,
            timestamp=datetime(2024, 1, i + 1, tzinfo=timezone.utc),
            open=100.0 + i,
            high=105.0 + i,
            low=99.0 + i,
            close=102.0 + i,
            volume=50000.0 + i * 1000,
        )
        db_session.add(r)
    db_session.flush()  # make visible within the shared transaction


class TestStockHistory:
    def test_returns_bars(self, client, db_session):
        _seed_prices(db_session, symbol="SBIN", count=5)
        res = client.get("/api/stocks/SBIN/history?exchange=NSE")
        assert res.status_code == 200
        data = res.json()
        assert data["symbol"] == "SBIN"
        assert data["exchange"] == "NSE"
        assert data["total"] == 5
        assert len(data["items"]) == 5

    def test_symbol_normalised(self, client, db_session):
        _seed_prices(db_session, symbol="HDFC", exchange="NSE", count=3)
        res = client.get("/api/stocks/hdfc/history")
        assert res.status_code == 200
        assert res.json()["total"] == 3

    def test_empty_symbol_returns_empty(self, client):
        res = client.get("/api/stocks/UNKNOWN99/history")
        assert res.status_code == 200
        assert res.json()["total"] == 0

    def test_date_filtering_start(self, client, db_session):
        _seed_prices(db_session, symbol="AXISBANK", count=10)
        # Start from 2024-01-06 → should return bars 6–10
        res = client.get("/api/stocks/AXISBANK/history?start=2024-01-06")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 5

    def test_bar_fields_present(self, client, db_session):
        _seed_prices(db_session, symbol="NTPC", count=1)
        res = client.get("/api/stocks/NTPC/history")
        assert res.status_code == 200
        bar = res.json()["items"][0]
        for field in ("symbol", "exchange", "timestamp", "open", "high", "low", "close", "volume"):
            assert field in bar
