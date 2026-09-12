"""
tests/test_notifications.py
----------------------------
Comprehensive tests for ConsoleNotificationProvider, EmailNotificationProvider,
and NotificationService.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.database.models import AlertRecord, Base, NotificationDelivery, User, WatchlistItem
from backend.app.database.repository import (
    create_alert,
    create_notification_delivery,
    create_user,
    get_notification_delivery,
)
from backend.app.notifications.base import NotificationProvider
from backend.app.notifications.console import ConsoleNotificationProvider
from backend.app.notifications.email import DISCLAIMER_TEXT, EmailNotificationProvider
from backend.app.notifications.service import NotificationService


@pytest.fixture
def memory_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestingSession()
    yield session
    session.close()


@pytest.fixture
def sample_alert(memory_db: Session) -> AlertRecord:
    return create_alert(
        db=memory_db,
        alert_id="ALERT-TEST-001",
        symbol="TCS",
        action="BUY",
        severity=8,
        message="Strong historical outperformance on earnings beat.",
        user_id=None,
        should_alert=True,
    )


# ---------------------------------------------------------------------------
# 1. Console Notification Provider Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_console_provider_outputs_alert(capsys):
    provider = ConsoleNotificationProvider(enabled=True)
    ctx = {
        "symbol": "TCS",
        "company_name": "Tata Consultancy Services",
        "action": "BUY",
        "sentiment": "positive",
        "event_type": "EARNINGS_BEAT",
        "severity": 8,
        "confidence": 0.825,
        "evidence_strength": "STRONG",
        "historical_signal": "STRONG_POSITIVE",
        "sample_size_1d": 45,
        "positive_rate_1d": 0.7333,
        "mean_excess_return_1d": 0.0215,
        "headline": "TCS reports 12% revenue growth in Q3",
        "reason": "Similar historical events produced positive excess returns.",
    }

    await provider.send(
        user_email="trader@example.com",
        alert_id="ALERT-TEST-001",
        context=ctx,
    )

    captured = capsys.readouterr().out
    assert "STOCK ALERT" in captured
    assert "trader@example.com" in captured
    assert "TCS" in captured
    assert "Tata Consultancy Services" in captured
    assert "BUY" in captured
    assert "0.8250" in captured
    assert "+2.15%" in captured
    assert "DISCLAIMER:" in captured


@pytest.mark.asyncio
async def test_console_provider_disabled_suppresses_output(capsys):
    provider = ConsoleNotificationProvider(enabled=False)
    await provider.send(
        user_email="trader@example.com",
        alert_id="ALERT-TEST-001",
        context={"symbol": "INFY"},
    )
    captured = capsys.readouterr().out
    assert captured == ""


@pytest.mark.asyncio
async def test_console_provider_handles_missing_fields_gracefully(capsys):
    provider = ConsoleNotificationProvider(enabled=True)
    # Minimal context with missing fields
    await provider.send(
        user_email="trader@example.com",
        alert_id="ALERT-MINIMAL",
        context={},
    )
    captured = capsys.readouterr().out
    assert "STOCK ALERT" in captured
    assert "ALERT-MINIMAL" in captured


# ---------------------------------------------------------------------------
# 2. Email Notification Provider Tests
# ---------------------------------------------------------------------------

def test_email_content_builder():
    provider = EmailNotificationProvider(enabled=True)
    ctx = {
        "symbol": "RELIANCE",
        "company_name": "Reliance Industries",
        "action": "SELL",
        "event_type": "REGULATORY_FINE",
        "sentiment": "negative",
        "severity": 9,
        "confidence": 0.78,
        "sample_size_1d": 32,
        "positive_rate_1d": 0.25,
        "mean_excess_return_1d": -0.0185,
        "headline": "Regulator imposes penalty on subsidiary",
        "reason": "High negative event study rate.",
        "published_at": datetime(2026, 4, 15, 10, 30, tzinfo=timezone.utc),
    }

    subject, body = provider.build_email_content("ALERT-REL-01", ctx)
    assert subject == "[Stock Alert] RELIANCE - SELL"
    assert "Reliance Industries" in body
    assert "REGULATORY_FINE" in body
    assert "9/10" in body
    assert "0.7800" in body
    assert "-1.85%" in body
    assert "Regulator imposes penalty" in body
    assert DISCLAIMER_TEXT in body


@pytest.mark.asyncio
async def test_email_provider_sends_via_mock_smtp():
    mock_smtp_client = MagicMock()
    mock_factory = MagicMock(return_value=mock_smtp_client)

    provider = EmailNotificationProvider(
        host="smtp.fake.local",
        enabled=True,
        smtp_factory=mock_factory,
    )

    ctx = {"symbol": "INFY", "action": "BUY", "company_name": "Infosys Ltd"}
    await provider.send("investor@example.com", "ALERT-INFY-1", ctx)

    assert mock_smtp_client.send_message.called
    sent_msg = mock_smtp_client.send_message.call_args[0][0]
    assert sent_msg["To"] == "investor@example.com"
    assert "[Stock Alert] INFY - BUY" in sent_msg["Subject"]


@pytest.mark.asyncio
async def test_email_provider_retries_transient_failure():
    mock_smtp_client = MagicMock()
    # Fail twice, succeed on 3rd attempt
    mock_smtp_client.send_message.side_effect = [
        Exception("Connection reset"),
        Exception("Timeout"),
        None,
    ]
    mock_factory = MagicMock(return_value=mock_smtp_client)

    provider = EmailNotificationProvider(
        host="smtp.fake.local",
        enabled=True,
        max_retries=3,
        smtp_factory=mock_factory,
    )

    with patch("time.sleep"):  # avoid test sleep delays
        await provider.send("investor@example.com", "ALERT-RETRY", {"symbol": "SBIN"})

    assert mock_smtp_client.send_message.call_count == 3


@pytest.mark.asyncio
async def test_email_provider_fails_gracefully_when_max_retries_exceeded():
    mock_smtp_client = MagicMock()
    mock_smtp_client.send_message.side_effect = Exception("Persistent SMTP error")
    mock_factory = MagicMock(return_value=mock_smtp_client)

    provider = EmailNotificationProvider(
        host="smtp.fake.local",
        enabled=True,
        max_retries=2,
        smtp_factory=mock_factory,
    )

    with patch("time.sleep"):
        with pytest.raises(RuntimeError, match="SMTP delivery failed"):
            await provider.send("investor@example.com", "ALERT-FAIL", {"symbol": "SBIN"})


# ---------------------------------------------------------------------------
# 3. Notification Service Tests
# ---------------------------------------------------------------------------

class FakeProvider(NotificationProvider):
    def __init__(self, name: str = "fake", should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.sent_calls = []

    async def send(self, user_email: str, alert_id: str, context: Dict[str, Any]) -> None:
        if self.should_fail:
            raise RuntimeError(f"Channel {self.name} simulated outage")
        self.sent_calls.append((user_email, alert_id, context))


@pytest.mark.asyncio
async def test_service_filters_by_active_watchlist(memory_db: Session, sample_alert: AlertRecord):
    user1 = User(email="user1@example.com", is_active=True)
    user2 = User(email="user2@example.com", is_active=True)
    user3 = User(email="user3@example.com", is_active=False)  # inactive
    memory_db.add_all([user1, user2, user3])
    memory_db.commit()

    # user1 watches TCS (matches alert)
    # user2 watches INFY (does not match alert)
    # user3 watches TCS (matches alert but is inactive)
    w1 = WatchlistItem(user_id=user1.id, symbol="TCS", company_name="Tata Consultancy")
    w2 = WatchlistItem(user_id=user2.id, symbol="INFY", company_name="Infosys")
    w3 = WatchlistItem(user_id=user3.id, symbol="TCS", company_name="Tata Consultancy")
    memory_db.add_all([w1, w2, w3])
    memory_db.commit()

    active_users_watchlists = [
        (user1, [w1]),
        (user2, [w2]),
        (user3, [w3]),
    ]

    provider = FakeProvider(name="mock_channel")
    service = NotificationService(providers=[provider])

    count = await service.notify_eligible_users(
        db=memory_db,
        alert=sample_alert,
        active_users_and_watchlists=active_users_watchlists,
        context={"headline": "TCS Q3 Results"},
    )

    assert count == 1
    assert len(provider.sent_calls) == 1
    recipient, alert_id, ctx = provider.sent_calls[0]
    assert recipient == "user1@example.com"
    assert alert_id == "ALERT-TEST-001"
    assert ctx["headline"] == "TCS Q3 Results"

    # Verify delivery record persisted as 'sent'
    delivery = get_notification_delivery(memory_db, "ALERT-TEST-001", user1.id, "mock_channel")
    assert delivery is not None
    assert delivery.status == "sent"


@pytest.mark.asyncio
async def test_service_duplicate_protection(memory_db: Session, sample_alert: AlertRecord):
    user = User(email="investor@example.com", is_active=True)
    memory_db.add(user)
    memory_db.commit()
    w = WatchlistItem(user_id=user.id, symbol="TCS", company_name="Tata Consultancy")
    memory_db.add(w)
    memory_db.commit()

    provider = FakeProvider(name="test_chan")
    service = NotificationService(providers=[provider])

    active_list = [(user, [w])]

    # First delivery
    first_sent = await service.notify_eligible_users(memory_db, sample_alert, active_list)
    assert first_sent == 1
    assert len(provider.sent_calls) == 1

    # Second delivery with SAME alert and user -> must be skipped by idempotency
    second_sent = await service.notify_eligible_users(memory_db, sample_alert, active_list)
    assert second_sent == 0
    assert len(provider.sent_calls) == 1  # No additional calls


@pytest.mark.asyncio
async def test_service_records_failure_and_does_not_crash(memory_db: Session, sample_alert: AlertRecord):
    user = User(email="investor@example.com", is_active=True)
    memory_db.add(user)
    memory_db.commit()
    w = WatchlistItem(user_id=user.id, symbol="TCS", company_name="Tata Consultancy")
    memory_db.add(w)
    memory_db.commit()

    failing_provider = FakeProvider(name="broken_chan", should_fail=True)
    service = NotificationService(providers=[failing_provider])

    active_list = [(user, [w])]
    sent_count = await service.notify_eligible_users(memory_db, sample_alert, active_list)

    assert sent_count == 0
    # Delivery record must exist with status "failed"
    deliv = get_notification_delivery(memory_db, sample_alert.alert_id, user.id, "broken_chan")
    assert deliv is not None
    assert deliv.status == "failed"
    assert "simulated outage" in (deliv.error_message or "")


@pytest.mark.asyncio
async def test_service_skips_when_should_alert_is_false(memory_db: Session):
    user = User(email="u@example.com", is_active=True)
    memory_db.add(user)
    memory_db.commit()
    w = WatchlistItem(user_id=user.id, symbol="TCS", company_name="Tata Consultancy")
    memory_db.add(w)
    memory_db.commit()

    non_alert = create_alert(
        db=memory_db,
        alert_id="ALERT-NOOP-001",
        symbol="TCS",
        action="NO_ACTION",
        severity=2,
        message="Routine news, no action.",
        should_alert=False,
    )

    provider = FakeProvider()
    service = NotificationService(providers=[provider])
    sent = await service.notify_eligible_users(memory_db, non_alert, [(user, [w])])
    assert sent == 0
    assert len(provider.sent_calls) == 0
