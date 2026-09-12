"""
tests/api/test_users.py
-------------------------
Tests for User and Preferences API endpoints.

POST   /api/users
GET    /api/users/{user_id}
GET    /api/users/{user_id}/preferences
PUT    /api/users/{user_id}/preferences
"""


class TestUserCreate:
    def test_create_user_returns_201(self, client):
        res = client.post("/api/users", json={"email": "alice@example.com"})
        assert res.status_code == 201
        data = res.json()
        assert data["email"] == "alice@example.com"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    def test_create_user_idempotent(self, client):
        """POSTing the same email twice returns the existing user."""
        res1 = client.post("/api/users", json={"email": "bob@example.com"})
        res2 = client.post("/api/users", json={"email": "bob@example.com"})
        assert res1.status_code == 201
        assert res2.status_code == 201
        assert res1.json()["id"] == res2.json()["id"]

    def test_create_user_normalises_email(self, client):
        res = client.post("/api/users", json={"email": "  CHARLIE@Example.COM  "})
        assert res.status_code == 201
        assert res.json()["email"] == "charlie@example.com"

    def test_create_user_missing_email_returns_422(self, client):
        res = client.post("/api/users", json={})
        assert res.status_code == 422


class TestGetUser:
    def test_get_existing_user(self, client):
        created = client.post("/api/users", json={"email": "dana@example.com"}).json()
        res = client.get(f"/api/users/{created['id']}")
        assert res.status_code == 200
        assert res.json()["email"] == "dana@example.com"

    def test_get_nonexistent_user_returns_404(self, client):
        res = client.get("/api/users/99999")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()


class TestUserPreferences:
    def test_get_preferences(self, client):
        user = client.post("/api/users", json={"email": "prefs@example.com"}).json()
        res = client.get(f"/api/users/{user['id']}/preferences")
        assert res.status_code == 200
        data = res.json()
        assert data["is_active"] is True
        assert data["email"] == "prefs@example.com"

    def test_update_preferences_deactivate(self, client):
        user = client.post("/api/users", json={"email": "deactivate@example.com"}).json()
        res = client.put(
            f"/api/users/{user['id']}/preferences",
            json={"is_active": False},
        )
        assert res.status_code == 200
        assert res.json()["is_active"] is False

    def test_update_preferences_nonexistent_user(self, client):
        res = client.put("/api/users/99999/preferences", json={"is_active": False})
        assert res.status_code == 404
