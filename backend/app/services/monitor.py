"""
backend/app/services/monitor.py
---------------------------------
24/7 Stock Screener Background Monitor.

Periodically inspects all active user watchlists, collects unique stock symbols,
fetches recent news via GDELT, deduplicates and checks relevance, runs the core
intelligence pipeline once per unique article, persists system-level AlertRecords,
and dispatches notifications to eligible watching users.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

from sqlalchemy.orm import Session, sessionmaker

from backend.app.api.schemas import severity_label_to_int
from backend.app.database.config import SessionLocal
from backend.app.database.models import AlertRecord
from backend.app.database.repository import (
    create_alert,
    get_active_users_with_watchlists,
    save_news_items,
)
from backend.app.models.news import NewsItem
from backend.app.notifications.service import NotificationService
from backend.app.providers.base import NewsProvider
from backend.app.providers.gdelt import GDELTNewsProvider
from backend.app.services.news_relevance import StockMetadata
from backend.app.services.pipeline import StockNewsPipeline

logger = logging.getLogger(__name__)


@dataclass
class MonitorCycleStats:
    """Statistics captured during a single monitor execution cycle."""

    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    stocks_monitored: int = 0
    articles_fetched: int = 0
    articles_unseen: int = 0
    articles_analyzed: int = 0
    alerts_generated: int = 0
    notifications_sent: int = 0
    errors_count: int = 0


class StockMonitor:
    """
    Background 24/7 monitoring engine.
    """

    def __init__(
        self,
        session_factory: Optional[sessionmaker] = None,
        news_provider: Optional[NewsProvider] = None,
        pipeline: Optional[StockNewsPipeline] = None,
        notification_service: Optional[NotificationService] = None,
        poll_interval_seconds: Optional[int] = None,
        sleep_fn: Optional[Callable[[float], Any]] = None,
    ) -> None:
        self.session_factory = session_factory or SessionLocal
        self.news_provider = news_provider or GDELTNewsProvider()
        self.pipeline = pipeline or StockNewsPipeline()
        self.notification_service = notification_service or NotificationService()
        self.sleep_fn = sleep_fn or asyncio.sleep

        # Resolve poll interval from arg or env
        if poll_interval_seconds is not None:
            self.poll_interval_seconds = max(1, int(poll_interval_seconds))
        else:
            raw_interval = os.getenv("MONITOR_POLL_INTERVAL_SECONDS", "300")
            try:
                self.poll_interval_seconds = max(1, int(raw_interval))
            except ValueError:
                logger.warning(
                    "Invalid MONITOR_POLL_INTERVAL_SECONDS=%r; defaulting to 300s",
                    raw_interval,
                )
                self.poll_interval_seconds = 300

        self._running: bool = False
        self._stop_event: asyncio.Event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self.last_cycle_stats: Optional[MonitorCycleStats] = None

    @property
    def is_running(self) -> bool:
        return self._running

    def get_status(self) -> Dict[str, Any]:
        """Return operational telemetry dictionary."""
        enabled_raw = os.getenv("MONITOR_ENABLED", "false").strip().lower()
        enabled = enabled_raw not in ("false", "0", "no", "off")

        last_at = None
        last_duration = 0.0
        stocks_mon = 0
        articles_proc = 0
        alerts_gen = 0

        if self.last_cycle_stats:
            last_at = self.last_cycle_stats.started_at.isoformat()
            last_duration = round(self.last_cycle_stats.duration_seconds, 2)
            stocks_mon = self.last_cycle_stats.stocks_monitored
            articles_proc = self.last_cycle_stats.articles_analyzed
            alerts_gen = self.last_cycle_stats.alerts_generated

        return {
            "enabled": enabled,
            "running": self._running,
            "poll_interval_seconds": self.poll_interval_seconds,
            "last_cycle_at": last_at,
            "last_cycle_duration_seconds": last_duration,
            "stocks_monitored": stocks_mon,
            "articles_processed": articles_proc,
            "alerts_generated": alerts_gen,
        }

    async def run_once(self) -> MonitorCycleStats:
        """
        Execute a single end-to-end monitoring cycle.

        1. Query database for all active users and their watchlists.
        2. Deduplicate symbols to construct a unique target stock set.
        3. For each unique symbol:
           a. Fetch news items via GDELT provider.
           b. Persist unseen news in the database (idempotency barrier).
           c. Pass unseen relevant news through the StockNewsPipeline ONCE.
           d. Persist AlertRecord if should_alert=True.
           e. Notify eligible watching users via NotificationService.
        4. Record and return execution telemetry.
        """
        start_time = time.monotonic()
        stats = MonitorCycleStats(started_at=datetime.now(timezone.utc))

        db: Session = self.session_factory()
        try:
            # 1. Load active users and watchlists
            users_and_watchlists = get_active_users_with_watchlists(db)
            if not users_and_watchlists:
                logger.info("Monitor cycle: no active users with watchlists found")
                stats.ended_at = datetime.now(timezone.utc)
                stats.duration_seconds = time.monotonic() - start_time
                self.last_cycle_stats = stats
                return stats

            # 2. Build unique stock map: symbol -> company_name
            unique_stocks: Dict[str, str] = {}
            for user, items in users_and_watchlists:
                for item in items:
                    sym = item.symbol.strip().upper()
                    if sym not in unique_stocks:
                        unique_stocks[sym] = item.company_name.strip()

            stats.stocks_monitored = len(unique_stocks)
            logger.info("Monitor cycle started: %d unique stocks to inspect", len(unique_stocks))

            # 3. Process each unique stock
            for symbol, company_name in unique_stocks.items():
                try:
                    await self._process_stock(
                        db=db,
                        symbol=symbol,
                        company_name=company_name,
                        users_and_watchlists=users_and_watchlists,
                        stats=stats,
                    )
                except Exception as exc:
                    stats.errors_count += 1
                    logger.exception("Failed processing stock %s in monitor cycle: %s", symbol, exc)

        except Exception as exc:
            stats.errors_count += 1
            logger.exception("Fatal error in monitor cycle: %s", exc)
        finally:
            db.close()
            stats.ended_at = datetime.now(timezone.utc)
            stats.duration_seconds = time.monotonic() - start_time
            self.last_cycle_stats = stats
            logger.info(
                "Monitor cycle finished in %.2fs. Stocks: %d, Articles analyzed: %d, Alerts: %d, Sent: %d",
                stats.duration_seconds,
                stats.stocks_monitored,
                stats.articles_analyzed,
                stats.alerts_generated,
                stats.notifications_sent,
            )

        return stats

    async def _process_stock(
        self,
        db: Session,
        symbol: str,
        company_name: str,
        users_and_watchlists: List[Any],
        stats: MonitorCycleStats,
    ) -> None:
        """Process news and generate alerts for one stock."""
        # A. Fetch news asynchronously via thread pool
        try:
            raw_news = await asyncio.to_thread(
                self.news_provider.fetch_news,
                symbol=symbol,
                company_name=company_name,
                limit=20,
            )
        except Exception as exc:
            stats.errors_count += 1
            logger.warning("News fetch failed for %s (%s): %s", symbol, company_name, exc)
            return

        if not raw_news:
            return

        stats.articles_fetched += len(raw_news)

        # B. Persist unseen news in the database
        # save_news_items() deduplicates using news_records.news_id uniqueness
        # and returns ONLY the newly inserted NewsRecord objects!
        new_records = save_news_items(db, raw_news)
        if not new_records:
            logger.debug("No unseen articles for %s", symbol)
            return

        stats.articles_unseen += len(new_records)

        # C. Reconstruct NewsItem models for newly saved records
        metadata = StockMetadata(
            symbol=symbol,
            company_name=company_name,
        )

        for rec in new_records:
            try:
                item = NewsItem(
                    news_id=rec.news_id,
                    symbol=rec.symbol,
                    company_name=rec.company_name,
                    title=rec.title,
                    content=rec.content,
                    source=rec.source,
                    url=rec.url,
                    published_at=rec.published_at,
                )

                # Process single news item through the full pipeline
                res = await asyncio.to_thread(
                    self.pipeline.process_news_item,
                    item=item,
                    metadata=metadata,
                )
                stats.articles_analyzed += 1

                # If alert generated, persist and dispatch notifications
                if res.should_alert:
                    stats.alerts_generated += 1
                    alert_id = f"ALERT-{rec.news_id}"
                    sev_int = severity_label_to_int(res.severity)

                    # Persist system-level AlertRecord (user_id=None)
                    alert_record = create_alert(
                        db=db,
                        alert_id=alert_id,
                        symbol=res.symbol,
                        action=res.action,
                        severity=sev_int,
                        message=res.reason[:2000] if res.reason else f"Alert triggered for {res.symbol}",
                        user_id=None,
                        should_alert=True,
                    )

                    # Context dict for notification providers
                    alert_ctx = {
                        "symbol": res.symbol,
                        "company_name": company_name,
                        "action": res.action,
                        "sentiment": res.sentiment,
                        "event_type": res.event_type,
                        "severity": sev_int,
                        "confidence": res.confidence,
                        "evidence_strength": res.evidence_strength,
                        "sample_size_1d": res.historical_sample_size,
                        "reason": res.reason,
                        "message": alert_record.message,
                        "headline": rec.title,
                        "published_at": rec.published_at,
                    }

                    sent = await self.notification_service.notify_eligible_users(
                        db=db,
                        alert=alert_record,
                        active_users_and_watchlists=users_and_watchlists,
                        context=alert_ctx,
                    )
                    stats.notifications_sent += sent

            except Exception as exc:
                stats.errors_count += 1
                logger.exception("Error analyzing article %s for %s: %s", rec.news_id, symbol, exc)

    async def run_forever(self) -> None:
        """Continuously loop until stopped."""
        self._running = True
        self._stop_event.clear()
        logger.info("StockMonitor background loop started with interval=%ds", self.poll_interval_seconds)

        try:
            while not self._stop_event.is_set():
                try:
                    await self.run_once()
                except Exception as exc:
                    logger.exception("Unexpected error inside monitor cycle loop: %s", exc)

                # Wait for poll interval or until stop event is signaled
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=float(self.poll_interval_seconds))
                    break  # Stop was requested
                except asyncio.TimeoutError:
                    continue  # Poll timeout elapsed, loop again
        finally:
            self._running = False
            logger.info("StockMonitor background loop terminated")

    def start(self) -> asyncio.Task:
        """Start the background monitor task if not already running."""
        if self._running or (self._task and not self._task.done()):
            logger.warning("StockMonitor already running, ignoring start() call")
            return self._task  # type: ignore

        self._running = True
        self._stop_event.clear()
        self._task = asyncio.create_task(self.run_forever())
        return self._task

    async def stop(self) -> None:
        """Gracefully stop the background monitor task."""
        if not self._running and not (self._task and not self._task.done()):
            return

        logger.info("Stopping StockMonitor...")
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        self._running = False
        logger.info("StockMonitor stopped successfully")
