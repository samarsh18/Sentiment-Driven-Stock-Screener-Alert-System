"""
backend/app/api/routers/monitor.py
-----------------------------------
Monitor status endpoints.

GET /api/monitor/status    Telemetry and health info for the 24/7 background monitor.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/monitor", tags=["Monitor"])

# Global monitor instance pointer (set by main.py lifespan)
_global_monitor: Optional[Any] = None


def set_global_monitor(monitor: Any) -> None:
    """Register the active StockMonitor instance with the router."""
    global _global_monitor
    _global_monitor = monitor


def get_global_monitor() -> Optional[Any]:
    """Retrieve the active StockMonitor instance if registered."""
    return _global_monitor


class MonitorStatusResponse(BaseModel):
    enabled: bool
    running: bool
    poll_interval_seconds: int = 300
    last_cycle_at: Optional[str] = None
    last_cycle_duration_seconds: float = 0.0
    stocks_monitored: int = 0
    articles_processed: int = 0
    alerts_generated: int = 0


@router.get("/status", response_model=MonitorStatusResponse)
def get_monitor_status() -> MonitorStatusResponse:
    """
    Return operational status of the 24/7 news monitoring background service.
    """
    if _global_monitor is not None:
        data = _global_monitor.get_status()
        return MonitorStatusResponse(**data)

    enabled_raw = os.getenv("MONITOR_ENABLED", "false").strip().lower()
    enabled = enabled_raw not in ("false", "0", "no", "off")

    return MonitorStatusResponse(
        enabled=enabled,
        running=False,
        poll_interval_seconds=int(os.getenv("MONITOR_POLL_INTERVAL_SECONDS", "300")),
        last_cycle_at=None,
        last_cycle_duration_seconds=0.0,
        stocks_monitored=0,
        articles_processed=0,
        alerts_generated=0,
    )
