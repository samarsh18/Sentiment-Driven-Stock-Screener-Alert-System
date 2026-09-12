"""
backend/app/notifications/base.py
-----------------------------------
Abstract base class for all notification providers.

Design principles:
- Providers are stateless per send() call.
- Errors must be raised as exceptions; callers decide whether to swallow or log.
- The interface is intentionally thin so adding Telegram, Slack, WhatsApp etc.
  requires only implementing send().

Context dict keys (all optional, providers pick what they need):
    symbol          : str     — stock ticker
    company_name    : str     — human-readable company name
    action          : str     — BUY / SELL / ALERT_POSITIVE / etc.
    sentiment       : str     — positive / negative / neutral
    event_type      : str
    severity        : int     — 1-10
    confidence      : float   — 0-1
    evidence_strength : str   — STRONG / MODERATE / WEAK / INSUFFICIENT
    historical_signal : str
    sample_size_1d  : int
    positive_rate_1d : float | None
    mean_excess_return_1d : float | None
    reason          : str     — human-readable explanation
    message         : str     — short alert message from the decision engine
    headline        : str     — original news headline
    published_at    : datetime
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class NotificationProvider(ABC):
    """
    Abstract interface for a notification delivery channel.

    Subclasses must implement `name` and `send()`.
    """

    #: Short identifier for this channel (e.g. "console", "email", "telegram")
    name: str = "unknown"

    @abstractmethod
    async def send(
        self,
        user_email: str,
        alert_id: str,
        context: Dict[str, Any],
    ) -> None:
        """
        Deliver a notification to one user.

        Parameters
        ----------
        user_email : str
            Recipient's email address (used as identity/address by most channels).
        alert_id : str
            Unique alert identifier (for logging and deduplication reference).
        context : Dict[str, Any]
            Rich context dict containing all alert evidence fields.  See module
            docstring for standard keys.  Providers must gracefully handle missing
            keys (use .get() with defaults).

        Raises
        ------
        Exception
            Any exception indicates delivery failure.  The NotificationService
            will catch, log, and persist a "failed" delivery record.
        """
        ...  # pragma: no cover
