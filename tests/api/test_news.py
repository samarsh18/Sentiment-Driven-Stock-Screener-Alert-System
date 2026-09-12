"""
tests/api/test_news.py
------------------------
Tests for News API endpoints.

GET /api/users/{user_id}/news
GET /api/news/{news_id}
GET /api/stocks/{symbol}/news
"""
from datetime import datetime, timezone

from backend.app.database.models import NewsRecord


def _create_user(client, email="news@example.com"):
    return client.post("/api/users", json={"email": email}).json()


def _seed_news(db_session, symbol="TCS", count=3):
    """Insert `count` NewsRecord rows for `symbol` into the test DB."""
    records = []
    for i in range(count):
        r = NewsRecord(
            news_id=f"{symbol}-test-{i:04d}",
            symbol=symbol,
            company_name=f"{symbol} Ltd",
            title=f"{symbol} news article {i}",
            content=f"Content for article {i}",
            source="TestSource",
            url=f"https://example.com/{symbol}/{i}",
            published_at=datetime(2024, 1, i + 1, tzinfo=timezone.utc),
        )
        db_session.add(r)
        records.append(r)
    db_session.flush()  # make visible within the shared transaction
    return records


class TestUserNews:
    def test_empty_watchlist_returns_empty_list(self, client):
        user = _create_user(client, "empty_news@example.com")
        res = client.get(f"/api/users/{user['id']}/news")
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["pagination"]["total"] == 0

    def test_nonexistent_user_returns_404(self, client):
        res = client.get("/api/users/99999/news")
        assert res.status_code == 404

    def test_returns_news_for_watchlist_symbols(self, client, db_session):
        user = _create_user(client, "watchnews@example.com")
        # Add TCS to watchlist
        client.post(
            f"/api/users/{user['id']}/watchlist",
            json={"symbol": "TCS", "company_name": "Tata Consultancy"},
        )
        _seed_news(db_session, symbol="TCS", count=5)
        _seed_news(db_session, symbol="INFY", count=3)  # not in watchlist

        res = client.get(f"/api/users/{user['id']}/news")
        assert res.status_code == 200
        data = res.json()
        assert data["pagination"]["total"] == 5
        for item in data["items"]:
            assert item["symbol"] == "TCS"

    def test_pagination(self, client, db_session):
        user = _create_user(client, "pagnews@example.com")
        client.post(
            f"/api/users/{user['id']}/watchlist",
            json={"symbol": "INFY", "company_name": "Infosys"},
        )
        _seed_news(db_session, symbol="INFY", count=10)

        res = client.get(f"/api/users/{user['id']}/news?limit=4&offset=0")
        assert res.status_code == 200
        data = res.json()
        assert len(data["items"]) == 4
        assert data["pagination"]["total"] == 10
        assert data["pagination"]["limit"] == 4


class TestGetNewsByNewsId:
    def test_returns_correct_record(self, client, db_session):
        _seed_news(db_session, symbol="WIPRO", count=1)
        res = client.get("/api/news/WIPRO-test-0000")
        assert res.status_code == 200
        assert res.json()["news_id"] == "WIPRO-test-0000"

    def test_nonexistent_news_id_returns_404(self, client):
        res = client.get("/api/news/NONEXISTENT-id-1234")
        assert res.status_code == 404


class TestGetStockNews:
    def test_returns_news_for_symbol(self, client, db_session):
        _seed_news(db_session, symbol="RELIANCE", count=4)
        res = client.get("/api/stocks/RELIANCE/news")
        assert res.status_code == 200
        data = res.json()
        assert data["pagination"]["total"] == 4
        for item in data["items"]:
            assert item["symbol"] == "RELIANCE"

    def test_symbol_case_insensitive(self, client, db_session):
        _seed_news(db_session, symbol="HDFC", count=2)
        res = client.get("/api/stocks/hdfc/news")
        assert res.status_code == 200
        assert res.json()["pagination"]["total"] == 2

    def test_empty_symbol_returns_empty(self, client):
        res = client.get("/api/stocks/UNKNOWN_SYM/news")
        assert res.status_code == 200
        assert res.json()["pagination"]["total"] == 0
