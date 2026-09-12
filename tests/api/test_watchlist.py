"""
tests/api/test_watchlist.py
-----------------------------
Tests for Watchlist API endpoints.

GET    /api/users/{user_id}/watchlist
POST   /api/users/{user_id}/watchlist
DELETE /api/users/{user_id}/watchlist/{symbol}
"""


def _create_user(client, email="watch@example.com"):
    return client.post("/api/users", json={"email": email}).json()


class TestGetWatchlist:
    def test_empty_watchlist(self, client):
        user = _create_user(client)
        res = client.get(f"/api/users/{user['id']}/watchlist")
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_nonexistent_user_returns_404(self, client):
        res = client.get("/api/users/99999/watchlist")
        assert res.status_code == 404


class TestAddWatchlistItem:
    def test_add_item_returns_201(self, client):
        user = _create_user(client, "add@example.com")
        res = client.post(
            f"/api/users/{user['id']}/watchlist",
            json={"symbol": "TCS", "company_name": "Tata Consultancy Services"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["symbol"] == "TCS"
        assert data["company_name"] == "Tata Consultancy Services"
        assert data["user_id"] == user["id"]

    def test_add_same_symbol_idempotent(self, client):
        user = _create_user(client, "idem@example.com")
        body = {"symbol": "INFY", "company_name": "Infosys"}
        r1 = client.post(f"/api/users/{user['id']}/watchlist", json=body)
        r2 = client.post(f"/api/users/{user['id']}/watchlist", json=body)
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["id"] == r2.json()["id"]

    def test_symbol_normalised_to_uppercase(self, client):
        user = _create_user(client, "upper@example.com")
        res = client.post(
            f"/api/users/{user['id']}/watchlist",
            json={"symbol": "reliance", "company_name": "Reliance Industries"},
        )
        assert res.status_code == 201
        assert res.json()["symbol"] == "RELIANCE"

    def test_add_missing_symbol_returns_422(self, client):
        user = _create_user(client, "missing@example.com")
        res = client.post(
            f"/api/users/{user['id']}/watchlist",
            json={"company_name": "Infosys"},
        )
        assert res.status_code == 422

    def test_add_nonexistent_user_returns_404(self, client):
        res = client.post(
            "/api/users/99999/watchlist",
            json={"symbol": "TCS", "company_name": "Tata Consultancy"},
        )
        assert res.status_code == 404


class TestRemoveWatchlistItem:
    def test_remove_existing_item(self, client):
        user = _create_user(client, "remove@example.com")
        client.post(
            f"/api/users/{user['id']}/watchlist",
            json={"symbol": "WIPRO", "company_name": "Wipro Ltd"},
        )
        res = client.delete(f"/api/users/{user['id']}/watchlist/WIPRO")
        assert res.status_code == 204

        # Verify it's gone
        wl = client.get(f"/api/users/{user['id']}/watchlist").json()
        assert wl["total"] == 0

    def test_remove_nonexistent_symbol_returns_404(self, client):
        user = _create_user(client, "noremove@example.com")
        res = client.delete(f"/api/users/{user['id']}/watchlist/NONEXISTENT")
        assert res.status_code == 404

    def test_watchlist_items_returned_after_add(self, client):
        user = _create_user(client, "multi@example.com")
        for sym, name in [("TCS", "TCS Ltd"), ("INFY", "Infosys"), ("WIPRO", "Wipro")]:
            client.post(
                f"/api/users/{user['id']}/watchlist",
                json={"symbol": sym, "company_name": name},
            )
        wl = client.get(f"/api/users/{user['id']}/watchlist").json()
        assert wl["total"] == 3
        symbols = {item["symbol"] for item in wl["items"]}
        assert symbols == {"TCS", "INFY", "WIPRO"}
