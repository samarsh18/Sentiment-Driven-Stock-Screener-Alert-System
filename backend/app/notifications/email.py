"""
backend/app/notifications/email.py
-----------------------------------
SMTP Email Notification Provider.

Delivers formatted stock alerts via SMTP (plain text, TLS optional).
All configuration is read from environment variables or constructor arguments.

Config keys:
    SMTP_HOST       (e.g. smtp.gmail.com, mailhog)
    SMTP_PORT       (default: 587)
    SMTP_USERNAME
    SMTP_PASSWORD
    SMTP_FROM_EMAIL (e.g. alerts@screener.local)
    SMTP_USE_TLS    (default: true)
    NOTIFICATIONS_ENABLED (default: true)
"""

from __future__ import annotations

import asyncio
import email.message
import logging
import os
import smtplib
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from backend.app.notifications.base import NotificationProvider

logger = logging.getLogger(__name__)

DISCLAIMER_TEXT = (
    "DISCLAIMER: Historical performance does not guarantee future results. "
    "Confidence is evidence-based but not certainty. "
    "This alert is for informational purposes only and does not constitute investment advice."
)


def _fmt_pct(val: Any) -> str:
    try:
        return f"{float(val) * 100:+.2f}%"
    except (TypeError, ValueError):
        return "N/A"


def _fmt_float(val: Any, decimals: int = 4) -> str:
    try:
        return f"{float(val):.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"


class EmailNotificationProvider(NotificationProvider):
    """
    SMTP email notification provider with retry capability.
    """

    name: str = "email"

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        from_email: Optional[str] = None,
        use_tls: Optional[bool] = None,
        enabled: Optional[bool] = None,
        max_retries: int = 3,
        smtp_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.host = host or os.getenv("SMTP_HOST", "")
        self.port = int(port or os.getenv("SMTP_PORT", "587"))
        self.username = username or os.getenv("SMTP_USERNAME", "")
        self.password = password or os.getenv("SMTP_PASSWORD", "")
        self.from_email = from_email or os.getenv("SMTP_FROM_EMAIL", "alerts@screener.local")
        self.max_retries = max_retries
        self._smtp_factory = smtp_factory

        if use_tls is None:
            raw_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower()
            self.use_tls = raw_tls not in ("false", "0", "no", "off")
        else:
            self.use_tls = use_tls

        if enabled is None:
            raw_enabled = os.getenv("NOTIFICATIONS_ENABLED", "true").strip().lower()
            self._enabled = raw_enabled not in ("false", "0", "no", "off")
        else:
            self._enabled = enabled

    @property
    def is_configured(self) -> bool:
        """True if sufficient SMTP host info is provided or custom factory is given."""
        return bool(self._smtp_factory or self.host.strip())

    def build_email_content(self, alert_id: str, context: Dict[str, Any]) -> tuple[str, str]:
        """Generate subject and plain-text body from context dict."""
        symbol = context.get("symbol", "ALERT").upper()
        action = context.get("action", "ALERT").upper()
        company = context.get("company_name", symbol)
        sentiment = context.get("sentiment", "neutral")
        event_type = context.get("event_type", "GENERAL_NEWS")
        severity = context.get("severity", 5)
        confidence = _fmt_float(context.get("confidence"), 4)
        sample = context.get("sample_size_1d", 0)
        pos_rate = _fmt_float(context.get("positive_rate_1d"), 4) if context.get("positive_rate_1d") is not None else "N/A"
        mean_excess = _fmt_pct(context.get("mean_excess_return_1d"))
        headline = context.get("headline") or context.get("message") or "N/A"
        reason = context.get("reason") or "Triggered by news and market evidence."
        pub_at = context.get("published_at")
        if isinstance(pub_at, datetime):
            ts_str = pub_at.isoformat()
        else:
            ts_str = datetime.now(timezone.utc).isoformat()

        subject = f"[Stock Alert] {symbol} - {action}"

        body = f"""==================================================
STOCK ALERT NOTIFICATION
==================================================
Company:                 {company}
Ticker:                  {symbol}
Action:                  {action}
Event Type:              {event_type}
Sentiment:               {sentiment}
Severity:                {severity}/10
Confidence:              {confidence}
Historical Sample Size:  {sample}
Historical Positive Rate:{pos_rate}
Mean Excess Return (1D): {mean_excess}

Headline:
{headline}

Evidence Summary:
{reason}

Alert ID:   {alert_id}
Timestamp:  {ts_str}

--------------------------------------------------
{DISCLAIMER_TEXT}
==================================================
"""
        return subject, body

    def _send_sync(self, recipient: str, subject: str, body: str) -> None:
        """Synchronous SMTP sender with retry logic."""
        msg = email.message.EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.from_email
        msg["To"] = recipient
        msg.set_content(body)

        last_err = None
        for attempt in range(1, self.max_retries + 1):
            try:
                if self._smtp_factory:
                    client = self._smtp_factory()
                    if hasattr(client, "__enter__"):
                        with client as s:
                            if s is not client and hasattr(client, "send_message"):
                                client.send_message(msg)
                            else:
                                s.send_message(msg)
                    else:
                        client.send_message(msg)
                    return

                with smtplib.SMTP(self.host, self.port, timeout=10.0) as server:
                    if self.use_tls:
                        server.starttls()
                    if self.username and self.password:
                        server.login(self.username, self.password)
                    server.send_message(msg)
                return
            except Exception as exc:
                last_err = exc
                logger.warning(
                    "SMTP send attempt %d/%d failed for recipient=%s: %s",
                    attempt, self.max_retries, recipient, exc,
                )
                if attempt < self.max_retries:
                    import time
                    time.sleep(0.5 * attempt)

        raise RuntimeError(f"SMTP delivery failed after {self.max_retries} attempts: {last_err}") from last_err

    async def send(
        self,
        user_email: str,
        alert_id: str,
        context: Dict[str, Any],
    ) -> None:
        """Deliver email asynchronously via thread pool."""
        if not self._enabled:
            logger.debug("Email notifications disabled, skipping alert_id=%s", alert_id)
            return

        if not self.is_configured:
            logger.debug("SMTP not configured (no host), skipping email to %s", user_email)
            return

        subject, body = self.build_email_content(alert_id, context)
        await asyncio.to_thread(self._send_sync, user_email, subject, body)
        logger.info("Email notification delivered successfully to %s for alert %s", user_email, alert_id)
