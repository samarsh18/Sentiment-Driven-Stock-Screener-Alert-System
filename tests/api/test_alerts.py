"""
tests/api/test_alerts.py
--------------------------
Tests for Alerts API endpoints.

GET /api/users/{user_id}/alerts
GET /api/users/{user_id}/alerts/{alert_id}
"""
import uuid
from datetime import datetime, timezone

from backend.app.database.models import AlertRecord


def _create_user(client, email="alerts@example.com"):
    return client.post("/api/users", json={"email": email}).json()


def _seed_alerts(db_session, user_id, symbol="TCS", count=3):
    """Insert `count` AlertRecord rows for `user_id`."""
    records = []
    for i in range(count):
        r = AlertRecord(
            alert_id=f"alert-{symbol}-{i:04d}-{uuid.uuid4().hex[:6]}",
            user_id=user_id,
            symbol=symbol,
            action="RISK_ALERT",
            severity=5 + i,
            message=f"Test alert {i} for {symbol}",
            should_alert=True,
        )
        db_session.add(r)
        records.append(r)
    db_session.flush()  # make visible within the shared transaction
    return records


class TestGetUserAlerts:
    def test_empty_alerts(self, client):
        user = _create_user(client, "empty_alerts@example.com")
        res = client.get(f"/api/users/{user['id']}/alerts")
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["pagination"]["total"] == 0

    def test_nonexistent_user_returns_404(self, client):
        res = client.get("/api/users/99999/alerts")
        assert res.status_code == 404

    def test_returns_alerts_for_user(self, client, db_session):
        user = _create_user(client, "with_alerts@example.com")
        _seed_alerts(db_session, user["id"], count=3)

        res = client.get(f"/api/users/{user['id']}/alerts")
        assert res.status_code == 200
        data = res.json()
        assert data["pagination"]["total"] == 3
        assert len(data["items"]) == 3

    def test_severity_label_in_response(self, client, db_session):
        """Alerts must expose both integer severity and string severity_label."""
        user = _create_user(client, "severity_label@example.com")
        _seed_alerts(db_session, user["id"], symbol="INFY", count=1)

        res = client.get(f"/api/users/{user['id']}/alerts")
        assert res.status_code == 200
        item = res.json()["items"][0]
        assert "severity" in item
        assert "severity_label" in item
        assert isinstance(item["severity"], int)
        assert item["severity_label"] in ("LOW", "MEDIUM", "HIGH")

    def test_severity_label_mapping(self, client, db_session):
        """Verify severity_label matches the documented mapping."""
        user = _create_user(client, "sev_map@example.com")
        cases = [(2, "LOW"), (5, "MEDIUM"), (8, "HIGH")]
        for sev_int, expected_label in cases:
            r = AlertRecord(
                alert_id=f"sev-test-{sev_int}",
                user_id=user["id"],
                symbol="TEST",
                action="WATCH",
                severity=sev_int,
                message="severity mapping test",
                should_alert=True,
            )
            db_session.add(r)
        db_session.flush()  # make visible within the shared transaction

        res = client.get(f"/api/users/{user['id']}/alerts?limit=100")
        items = {item["severity"]: item["severity_label"] for item in res.json()["items"]}
        assert items[2] == "LOW"
        assert items[5] == "MEDIUM"
        assert items[8] == "HIGH"

    def test_pagination(self, client, db_session):
        user = _create_user(client, "pag_alerts@example.com")
        _seed_alerts(db_session, user["id"], count=8)

        res = client.get(f"/api/users/{user['id']}/alerts?limit=3&offset=0")
        assert res.status_code == 200
        data = res.json()
        assert len(data["items"]) == 3
        assert data["pagination"]["total"] == 8

    def test_only_own_alerts_returned(self, client, db_session):
        user_a = _create_user(client, "user_a@example.com")
        user_b = _create_user(client, "user_b@example.com")
        _seed_alerts(db_session, user_a["id"], count=3)
        _seed_alerts(db_session, user_b["id"], count=2)

        res = client.get(f"/api/users/{user_a['id']}/alerts")
        assert res.json()["pagination"]["total"] == 3


class TestGetAlertById:
    def test_returns_correct_alert(self, client, db_session):
        user = _create_user(client, "byid@example.com")
        alerts = _seed_alerts(db_session, user["id"], count=1)
        aid = alerts[0].alert_id

        res = client.get(f"/api/users/{user['id']}/alerts/{aid}")
        assert res.status_code == 200
        assert res.json()["alert_id"] == aid

    def test_nonexistent_alert_returns_404(self, client):
        user = _create_user(client, "noalert@example.com")
        res = client.get(f"/api/users/{user['id']}/alerts/nonexistent-id")
        assert res.status_code == 404

    def test_other_users_alert_returns_404(self, client, db_session):
        user_a = _create_user(client, "owner_a@example.com")
        user_b = _create_user(client, "owner_b@example.com")
        alerts = _seed_alerts(db_session, user_a["id"], count=1)
        aid = alerts[0].alert_id

        # user_b cannot access user_a's alert
        res = client.get(f"/api/users/{user_b['id']}/alerts/{aid}")
        assert res.status_code == 404
