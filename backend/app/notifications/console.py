"""
backend/app/notifications/console.py
--------------------------------------
Console (stdout) notification provider.

Prints a rich, human-readable alert box to stdout.  Intended for
development, testing, and demos.  Zero external dependencies.

Enabled by setting:
    CONSOLE_NOTIFICATIONS_ENABLED=true

Example output:
==================================================
STOCK ALERT
Symbol:                  RELIANCE
Company:                 Reliance Industries
Action:                  BUY
Sentiment:               positive
Event Type:              EARNINGS_BEAT
Severity:                8/10
Confidence:              0.73
Evidence Strength:       STRONG
Historical Signal:       STRONG_POSITIVE
Historical Sample Size:  47
Historical Positive Rate: 0.72
Mean Excess Return (1D): +1.23%
Headline: Reliance beats Q3 estimates with record profit
Alert ID: abc123
----
DISCLAIMER: Historical performance does not guarantee future results.
Confidence is evidence-based but not certainty.
==================================================
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

from backend.app.notifications.base import NotificationProvider

logger = logging.getLogger(__name__)

_SEPARATOR = "=" * 56


def _fmt_pct(val: Any) -> str:
    """Format a float as a percentage string, or 'N/A'."""
    try:
        return f"{float(val) * 100:+.2f}%"
    except (TypeError, ValueError):
        return "N/A"


def _fmt_float(val: Any, decimals: int = 4) -> str:
    try:
        return f"{float(val):.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"


class ConsoleNotificationProvider(NotificationProvider):
    """
    Prints a formatted stock alert to stdout.

    Controlled by the CONSOLE_NOTIFICATIONS_ENABLED env var (default true
    so developers see output immediately without configuring SMTP).
    """

    name: str = "console"

    def __init__(self, enabled: bool | None = None) -> None:
        if enabled is None:
            raw = os.getenv("CONSOLE_NOTIFICATIONS_ENABLED", "true").strip().lower()
            self._enabled = raw not in ("false", "0", "no", "off")
        else:
            self._enabled = enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def send(
        self,
        user_email: str,
        alert_id: str,
        context: Dict[str, Any],
    ) -> None:
        """Print the alert to stdout (async-compatible; no I/O blocking)."""
        if not self._enabled:
            logger.debug("ConsoleNotificationProvider disabled — skipping alert %s", alert_id)
            return

        symbol = context.get("symbol", "?")
        company = context.get("company_name", "?")
        action = context.get("action", "?")
        sentiment = context.get("sentiment", "?")
        event_type = context.get("event_type", "?")
        severity = context.get("severity", "?")
        confidence = _fmt_float(context.get("confidence"), 4)
        evidence = context.get("evidence_strength", "?")
        signal = context.get("historical_signal", "?")
        sample = context.get("sample_size_1d", "?")
        pos_rate = _fmt_float(context.get("positive_rate_1d"), 4) if context.get("positive_rate_1d") is not None else "N/A"
        mean_return = _fmt_pct(context.get("mean_excess_return_1d"))
        headline = context.get("headline", context.get("message", ""))
        reason = context.get("reason", "")

        lines = [
            _SEPARATOR,
            "STOCK ALERT",
            f"To:                      {user_email}",
            f"Symbol:                  {symbol}",
            f"Company:                 {company}",
            f"Action:                  {action}",
            f"Sentiment:               {sentiment}",
            f"Event Type:              {event_type}",
            f"Severity:                {severity}/10",
            f"Confidence:              {confidence}",
            f"Evidence Strength:       {evidence}",
            f"Historical Signal:       {signal}",
            f"Historical Sample Size:  {sample}",
            f"Historical Positive Rate:{pos_rate}",
            f"Mean Excess Return (1D): {mean_return}",
            f"Headline:                {headline}",
            f"Reason:                  {reason}",
            f"Alert ID:                {alert_id}",
            "-" * 56,
            "DISCLAIMER: Historical performance does not guarantee future",
            "results. Confidence is evidence-based, not certainty.",
            "This is not investment advice.",
            _SEPARATOR,
        ]

        print("\n".join(lines), flush=True)
        logger.info(
            "Console notification sent: alert_id=%s symbol=%s user=%s action=%s",
            alert_id, symbol, user_email, action,
        )
