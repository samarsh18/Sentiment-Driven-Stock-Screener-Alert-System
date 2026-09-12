"""
tests/api/test_monitor_api.py
-----------------------------
API tests for the /api/monitor endpoints and health check.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from backend.app.api.routers.monitor import set_global_monitor
from backend.app.main import create_app
from backend.app.services.monitor import MonitorCycleStats


def test_health_check_endpoint():
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


def test_monitor_status_endpoint_default():
    set_global_monitor(None)
    with patch.dict(os.environ, {"MONITOR_ENABLED": "false", "MONITOR_POLL_INTERVAL_SECONDS": "180"}):
        app = create_app()
        with TestClient(app) as client:
            resp = client.get("/api/monitor/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["enabled"] is False
            assert data["running"] is False
            assert data["poll_interval_seconds"] == 180
            assert data["stocks_monitored"] == 0


def test_monitor_status_endpoint_with_active_monitor():
    mock_monitor = MagicMock()
    mock_monitor.get_status.return_value = {
        "enabled": True,
        "running": True,
        "poll_interval_seconds": 60,
        "last_cycle_at": "2026-05-10T12:00:00+00:00",
        "last_cycle_duration_seconds": 3.45,
        "stocks_monitored": 12,
        "articles_processed": 5,
        "alerts_generated": 2,
    }
    set_global_monitor(mock_monitor)

    try:
        app = create_app()
        with TestClient(app) as client:
            resp = client.get("/api/monitor/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["enabled"] is True
            assert data["running"] is True
            assert data["poll_interval_seconds"] == 60
            assert data["stocks_monitored"] == 12
            assert data["articles_processed"] == 5
            assert data["alerts_generated"] == 2
    finally:
        set_global_monitor(None)
