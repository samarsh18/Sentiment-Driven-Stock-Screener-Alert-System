"""
backend/app/main.py
---------------------
FastAPI application factory.

Configures CORS, initialises the database on startup, and registers
all API routers under the /api prefix.

To run locally:
    uvicorn backend.app.main:app --reload

Environment variables:
    DATABASE_URL    SQLAlchemy DSN   (default: sqlite:///./sentiment_screener.db)
    ALLOWED_ORIGINS Comma-separated CORS origins  (default: http://localhost:3000)
    LOG_LEVEL       Logging level    (default: INFO)
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.database.config import init_db

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CORS configuration
# ---------------------------------------------------------------------------
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
ALLOWED_ORIGINS: list[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(application: FastAPI):
    """Initialise the database on startup, start background monitor if enabled, clean up on shutdown."""
    logger.info("Starting up — initialising database tables.")
    init_db()

    monitor = None
    enabled_raw = os.getenv("MONITOR_ENABLED", "false").strip().lower()
    if enabled_raw not in ("false", "0", "no", "off"):
        logger.info("MONITOR_ENABLED is active — starting 24/7 background monitor.")
        from backend.app.api.routers.monitor import set_global_monitor
        from backend.app.services.monitor import StockMonitor

        monitor = StockMonitor()
        set_global_monitor(monitor)
        monitor.start()
    else:
        logger.info("MONITOR_ENABLED is false — background monitor not started.")

    yield

    if monitor is not None:
        logger.info("Shutting down — stopping background monitor.")
        await monitor.stop()

    logger.info("Shutting down.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
def create_app() -> FastAPI:
    application = FastAPI(
        title="Sentiment-Driven Stock Screener API",
        description=(
            "REST API for the Sentiment-Driven Stock Screener + Alert System. "
            "Provides user management, watchlist, news, alerts, market data, "
            "and deterministic pipeline analysis."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handler → consistent JSON errors
    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error.", "code": "INTERNAL_ERROR"},
        )

    # Routers
    from backend.app.api.routers import (
        alerts,
        monitor,
        news,
        pipeline,
        stocks,
        users,
        watchlist,
    )

    application.include_router(users.router)
    application.include_router(watchlist.router)
    application.include_router(news.router)
    application.include_router(alerts.router)
    application.include_router(stocks.router)
    application.include_router(pipeline.router)
    application.include_router(monitor.router)

    # Health check (no prefix, so not behind /api)
    @application.get("/health", tags=["Health"])
    def health():
        return {"status": "ok"}

    return application


app = create_app()
