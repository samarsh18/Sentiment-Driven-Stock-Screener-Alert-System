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
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.app.database.models import AlertRecord, NewsRecord, User, WatchlistItem
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