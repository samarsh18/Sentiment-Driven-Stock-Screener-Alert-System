"""
backend/app/notifications/service.py
-------------------------------------
NotificationService — Orchestrates alert delivery across configured channels.

Responsibilities:
1. Identify eligible users watching the stock associated with an AlertRecord.
2. Filter users by active preferences (e.g., user.is_active == True).
3. Check NotificationDelivery records for idempotency (never send same alert_id + user_id + channel twice).
4. Dispatch to all enabled providers (Console, Email, etc.).
5. Persist delivery status ("sent" or "failed") for audit and duplicate prevention.
6. Isolate failures: one failed recipient or channel never blocks others.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.app.database.models import AlertRecord, User, WatchlistItem
from backend.app.database.repository import (
    create_notification_delivery,
    get_notification_delivery,
)
from backend.app.notifications.base import NotificationProvider
from backend.app.notifications.console import ConsoleNotificationProvider
from backend.app.notifications.email import EmailNotificationProvider

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Central dispatcher for sending notifications to eligible users.
    """

    def __init__(
        self,
        providers: Optional[List[NotificationProvider]] = None,
    ) -> None:
        if providers is not None:
            self.providers = list(providers)
        else:
            self.providers = [
                ConsoleNotificationProvider(),
                EmailNotificationProvider(),
            ]

    def add_provider(self, provider: NotificationProvider) -> None:
        self.providers.append(provider)

    async def notify_eligible_users(
        self,
        db: Session,
        alert: AlertRecord,
        active_users_and_watchlists: List[Tuple[User, List[WatchlistItem]]],
        context: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Deliver notifications for an AlertRecord to all users watching the symbol.

        Parameters
        ----------
        db : Session
            Database session used for idempotency checks and delivery persistence.
        alert : AlertRecord
            The persisted alert record.
        active_users_and_watchlists : List[Tuple[User, List[WatchlistItem]]]
            Pre-loaded list of active users and their watchlist items.
        context : Optional[Dict[str, Any]]
            Additional context fields (sentiment, sample size, return stats, etc.).

        Returns
        -------
        int
            Count of successfully dispatched notifications (channel * user).
        """
        if not alert.should_alert:
            logger.debug("Alert %s should_alert=False, skipping notifications", alert.alert_id)
            return 0

        target_symbol = alert.symbol.strip().upper()
        alert_context = dict(context or {})
        alert_context.setdefault("symbol", target_symbol)
        alert_context.setdefault("action", alert.action)
        alert_context.setdefault("severity", alert.severity)
        alert_context.setdefault("message", alert.message)

        # 1. Filter eligible users
        eligible_users: List[User] = []
        for user, watchlist in active_users_and_watchlists:
            if not user.is_active:
                continue
            # Check if user watches this symbol
            is_watching = any(item.symbol.strip().upper() == target_symbol for item in watchlist)
            if is_watching:
                eligible_users.append(user)

        if not eligible_users:
            logger.debug("No active users watching %s for alert %s", target_symbol, alert.alert_id)
            return 0

        total_sent = 0

        # 2. Iterate each eligible user and provider
        for user in eligible_users:
            for provider in self.providers:
                channel = provider.name

                # Idempotency check: has this alert already been sent to this user on this channel?
                existing = get_notification_delivery(db, alert.alert_id, user.id, channel)
                if existing and existing.status == "sent":
                    logger.debug(
                        "Alert %s already sent to user %s via %s, skipping",
                        alert.alert_id, user.id, channel,
                    )
                    continue

                try:
                    await provider.send(
                        user_email=user.email,
                        alert_id=alert.alert_id,
                        context=alert_context,
                    )
                    create_notification_delivery(
                        db=db,
                        alert_id=alert.alert_id,
                        user_id=user.id,
                        channel=channel,
                        status="sent",
                    )
                    total_sent += 1
                except Exception as exc:
                    logger.warning(
                        "Notification failed for alert_id=%s user_id=%s channel=%s: %s",
                        alert.alert_id, user.id, channel, exc,
                    )
                    create_notification_delivery(
                        db=db,
                        alert_id=alert.alert_id,
                        user_id=user.id,
                        channel=channel,
                        status="failed",
                        error_message=str(exc)[:500],
                    )

        return total_sent
