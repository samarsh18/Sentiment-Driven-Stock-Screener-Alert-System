"""
backend/app/database/repository.py
-----------------------------------
Data Access Layer / Repository for the database module.

Provides clean CRUD helper functions for:
- News records persistence & querying
- User & Watchlist management
- Alert record persistence & querying
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import List, Optional, Union

from sqlalchemy.orm import Session

from backend.app.database.models import (
    AlertRecord,
    HistoricalPrice,
    NewsRecord,
    NotificationDelivery,
    User,
    WatchlistItem,
)
from backend.app.models.market import MarketDataBar
from backend.app.models.news import NewsItem

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. News Repository
# ---------------------------------------------------------------------------

def save_news_items(db: Session, news_items: List[NewsItem]) -> List[NewsRecord]:
    """
    Convert NewsItem Pydantic objects into NewsRecord ORM objects and persist them.

    Deduplication:
    Uses news_id as the deduplication key. If a record with the same news_id
    already exists in the database or earlier in the batch, duplicate entries
    are skipped and not re-inserted.

    Returns:
        List of newly created and persisted NewsRecord objects.
    """
    if not news_items:
        return []

    input_ids = [item.news_id for item in news_items]
    existing_records = db.query(NewsRecord.news_id).filter(NewsRecord.news_id.in_(input_ids)).all()
    existing_ids = {row.news_id for row in existing_records}

    new_records: List[NewsRecord] = []
    seen_ids = set(existing_ids)

    for item in news_items:
        if item.news_id in seen_ids:
            continue

        seen_ids.add(item.news_id)
        record = NewsRecord(
            news_id=item.news_id,
            symbol=item.symbol,
            company_name=item.company_name,
            title=item.title,
            content=item.content,
            source=item.source,
            url=item.url,
            published_at=item.published_at,
        )
        db.add(record)
        new_records.append(record)

    if new_records:
        db.commit()
        for r in new_records:
            db.refresh(r)

    return new_records


def get_news_by_symbol(db: Session, symbol: str, limit: int = 20) -> List[NewsRecord]:
    """
    Retrieve persisted news records for a stock symbol, newest published_at first.
    """
    clean_symbol = symbol.strip().upper()
    return (
        db.query(NewsRecord)
        .filter(NewsRecord.symbol == clean_symbol)
        .order_by(NewsRecord.published_at.desc())
        .limit(limit)
        .all()
    )


# ---------------------------------------------------------------------------
# 2. Watchlist & User Repository
# ---------------------------------------------------------------------------

def create_user(db: Session, email: str, is_active: bool = True) -> User:
    """
    Create a new application user, or return existing user if email is registered.
    """
    clean_email = email.strip().lower()
    existing = db.query(User).filter(User.email == clean_email).first()
    if existing:
        return existing

    user = User(email=clean_email, is_active=is_active)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """
    Retrieve a user by their primary key. Returns None if not found.
    """
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Retrieve a user by their email address. Returns None if not found.
    """
    clean_email = email.strip().lower()
    return db.query(User).filter(User.email == clean_email).first()


def add_watchlist_item(db: Session, user_id: int, symbol: str, company_name: str) -> WatchlistItem:
    """
    Add a stock symbol to a user's watchlist.
    If the (user_id, symbol) item already exists, returns the existing record.
    """
    clean_symbol = symbol.strip().upper()
    clean_company = company_name.strip()

    existing = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user_id, WatchlistItem.symbol == clean_symbol)
        .first()
    )
    if existing:
        return existing

    item = WatchlistItem(
        user_id=user_id,
        symbol=clean_symbol,
        company_name=clean_company,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_user_watchlist(db: Session, user_id: int) -> List[WatchlistItem]:
    """
    Retrieve all watchlist items for a given user.
    """
    return (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user_id)
        .order_by(WatchlistItem.created_at.desc())
        .all()
    )


def remove_watchlist_item(db: Session, user_id: int, symbol: str) -> bool:
    """
    Remove a stock symbol from a user's watchlist.
    Returns True if an item was deleted, False if no item matched.
    """
    clean_symbol = symbol.strip().upper()
    item = (
        db.query(WatchlistItem)
        .filter(WatchlistItem.user_id == user_id, WatchlistItem.symbol == clean_symbol)
        .first()
    )
    if not item:
        return False

    db.delete(item)
    db.commit()
    return True


# ---------------------------------------------------------------------------
# 3. Alert Persistence Repository
# ---------------------------------------------------------------------------

def create_alert(
    db: Session,
    alert_id: str,
    symbol: str,
    action: str,
    severity: int,
    message: str,
    user_id: Optional[int] = None,
    should_alert: bool = True,
) -> AlertRecord:
    """
    Persist an alert record generated by the decision engine.
    If an alert with alert_id already exists, returns existing record.
    """
    clean_symbol = symbol.strip().upper()
    clean_alert_id = alert_id.strip()

    existing = db.query(AlertRecord).filter(AlertRecord.alert_id == clean_alert_id).first()
    if existing:
        return existing

    alert = AlertRecord(
        alert_id=clean_alert_id,
        user_id=user_id,
        symbol=clean_symbol,
        action=action.strip(),
        severity=severity,
        message=message.strip(),
        should_alert=should_alert,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def get_alerts_by_user(db: Session, user_id: int, limit: int = 20) -> List[AlertRecord]:
    """
    Retrieve persisted alerts for a user, newest first.
    """
    return (
        db.query(AlertRecord)
        .filter(AlertRecord.user_id == user_id)
        .order_by(AlertRecord.created_at.desc())
        .limit(limit)
        .all()
    )


def get_alerts_by_symbol(db: Session, symbol: str, limit: int = 20) -> List[AlertRecord]:
    """
    Retrieve persisted alerts for a stock symbol, newest first.
    """
    clean_symbol = symbol.strip().upper()
    return (
        db.query(AlertRecord)
        .filter(AlertRecord.symbol == clean_symbol)
        .order_by(AlertRecord.created_at.desc())
        .limit(limit)
        .all()
    )


# ---------------------------------------------------------------------------
# 4. Market Data Persistence Repository
# ---------------------------------------------------------------------------

def _norm_utc_dt(dt: datetime) -> datetime:
    from datetime import timezone
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _dt_key(dt: datetime) -> datetime:
    return _norm_utc_dt(dt).replace(tzinfo=None)


def save_market_data(db: Session, items: List[MarketDataBar]) -> int:
    """
    Persist a list of MarketDataBar objects as HistoricalPrice ORM records.

    Deduplication:
    Uses (symbol, exchange, timestamp) as the logical unique key.
    Duplicate candles already in the database or in the same input batch are skipped.

    Returns:
        Number of newly persisted HistoricalPrice rows.
    """
    if not items:
        return 0

    candidates: List[tuple[MarketDataBar, datetime]] = []
    seen = set()

    for item in items:
        norm_ts = _norm_utc_dt(item.timestamp)
        key = (item.symbol, item.exchange, _dt_key(norm_ts))
        if key in seen:
            continue
        seen.add(key)
        candidates.append((item, norm_ts))

    if not candidates:
        return 0

    symbols = {item.symbol for item, _ in candidates}
    exchanges = {item.exchange for item, _ in candidates}

    existing_rows = (
        db.query(HistoricalPrice.symbol, HistoricalPrice.exchange, HistoricalPrice.timestamp)
        .filter(HistoricalPrice.symbol.in_(symbols), HistoricalPrice.exchange.in_(exchanges))
        .all()
    )
    existing_keys = {(r.symbol, r.exchange, _dt_key(r.timestamp)) for r in existing_rows}

    new_records: List[HistoricalPrice] = []
    for item, norm_ts in candidates:
        key = (item.symbol, item.exchange, _dt_key(norm_ts))
        if key in existing_keys:
            continue
        existing_keys.add(key)

        record = HistoricalPrice(
            symbol=item.symbol,
            exchange=item.exchange,
            timestamp=norm_ts,
            open=item.open,
            high=item.high,
            low=item.low,
            close=item.close,
            volume=item.volume,
        )
        db.add(record)
        new_records.append(record)

    if new_records:
        db.commit()

    return len(new_records)


def get_market_data(
    db: Session,
    symbol: str,
    exchange: str = "NSE",
    start_date: Optional[Union[datetime, date, str]] = None,
    end_date: Optional[Union[datetime, date, str]] = None,
) -> List[MarketDataBar]:
    """
    Retrieve persisted market data for a symbol and exchange, returning normalized MarketDataBar objects.

    Ordered chronologically (oldest timestamp first).
    """
    clean_symbol = symbol.strip().upper()
    clean_exchange = exchange.strip().upper()

    query = db.query(HistoricalPrice).filter(
        HistoricalPrice.symbol == clean_symbol,
        HistoricalPrice.exchange == clean_exchange,
    )

    if start_date is not None:
        start_dt = _parse_filter_date(start_date)
        if start_dt:
            query = query.filter(HistoricalPrice.timestamp >= start_dt)

    if end_date is not None:
        end_dt = _parse_filter_date(end_date)
        if end_dt:
            query = query.filter(HistoricalPrice.timestamp <= end_dt)

    rows = query.order_by(HistoricalPrice.timestamp.asc()).all()

    return [
        MarketDataBar(
            symbol=r.symbol,
            exchange=r.exchange,
            timestamp=r.timestamp,
            open=r.open,
            high=r.high,
            low=r.low,
            close=r.close,
            volume=r.volume,
        )
        for r in rows
    ]


def _parse_filter_date(val: Union[datetime, date, str]) -> Optional[datetime]:
    from datetime import timezone
    if isinstance(val, datetime):
        dt = val
    elif isinstance(val, date):
        dt = datetime.combine(val, datetime.min.time())
    elif isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# 5. Monitor Support Repository
# ---------------------------------------------------------------------------

def get_active_users_with_watchlists(db: Session) -> List[tuple[User, List[WatchlistItem]]]:
    """
    Load all active users together with their watchlist items in one query.

    Returns a list of (User, [WatchlistItem, ...]) tuples.
    Users with empty watchlists are excluded.
    """
    users = (
        db.query(User)
        .filter(User.is_active == True)  # noqa: E712
        .all()
    )
    result = []
    for user in users:
        items = (
            db.query(WatchlistItem)
            .filter(WatchlistItem.user_id == user.id)
            .all()
        )
        if items:
            result.append((user, items))
    return result


def get_notification_delivery(
    db: Session, alert_id: str, user_id: int, channel: str
) -> Optional[NotificationDelivery]:
    """
    Look up an existing notification delivery record.

    Returns the existing record if found, None otherwise.
    Used by NotificationService for idempotency checks.
    """
    return (
        db.query(NotificationDelivery)
        .filter(
            NotificationDelivery.alert_id == alert_id,
            NotificationDelivery.user_id == user_id,
            NotificationDelivery.channel == channel,
        )
        .first()
    )


def create_notification_delivery(
    db: Session,
    alert_id: str,
    user_id: int,
    channel: str,
    status: str,
    error_message: Optional[str] = None,
) -> Optional[NotificationDelivery]:
    """
    Persist a notification delivery record.

    Returns the newly created record, or the existing record if the
    (alert_id, user_id, channel) combination is already present (idempotent).

    Parameters
    ----------
    status : str
        "sent" or "failed".
    error_message : Optional[str]
        Error details when status is "failed".
    """
    from datetime import datetime, timezone

    existing = get_notification_delivery(db, alert_id, user_id, channel)
    if existing:
        return existing

    record = NotificationDelivery(
        alert_id=alert_id,
        user_id=user_id,
        channel=channel,
        status=status,
        error_message=error_message,
        sent_at=datetime.now(timezone.utc) if status == "sent" else None,
    )
    db.add(record)
    try:
        db.commit()
        db.refresh(record)
        return record
    except Exception as exc:
        db.rollback()
        logger.warning(
            "Failed to persist notification delivery for alert_id=%s user_id=%s channel=%s: %s",
            alert_id, user_id, channel, exc,
        )
        return None