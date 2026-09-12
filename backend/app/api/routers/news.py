"""
backend/app/api/routers/news.py
---------------------------------
News endpoints.

GET /api/users/{user_id}/news       Latest news for all symbols in user's watchlist
GET /api/news/{news_id}             Single news record by news_id
GET /api/stocks/{symbol}/news       Latest news for a specific symbol (no user context)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, require_user
from backend.app.api.schemas import NewsListResponse, NewsRecordResponse, PaginationMeta
from backend.app.database.models import NewsRecord
from backend.app.database.repository import get_news_by_symbol, get_user_watchlist

router = APIRouter(tags=["News"])


@router.get("/api/users/{user_id}/news", response_model=NewsListResponse)
def get_user_news(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(require_user),
    db: Session = Depends(get_db),
):
    """
    Return paginated news for all stocks on the user's watchlist,
    newest first.
    """
    watchlist = get_user_watchlist(db, user_id=user.id)
    if not watchlist:
        return NewsListResponse(
            items=[],
            pagination=PaginationMeta(total=0, limit=limit, offset=offset),
        )

    symbols = [item.symbol for item in watchlist]

    query = (
        db.query(NewsRecord)
        .filter(NewsRecord.symbol.in_(symbols))
        .order_by(NewsRecord.published_at.desc())
    )
    total = query.count()
    records = query.offset(offset).limit(limit).all()

    return NewsListResponse(
        items=records,
        pagination=PaginationMeta(total=total, limit=limit, offset=offset),
    )


@router.get("/api/news/{news_id}", response_model=NewsRecordResponse)
def get_news_by_id(news_id: str, db: Session = Depends(get_db)):
    """Return a single news record by its news_id."""
    record = db.query(NewsRecord).filter(NewsRecord.news_id == news_id).first()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"News record {news_id!r} not found.",
        )
    return record


@router.get("/api/stocks/{symbol}/news", response_model=NewsListResponse)
def get_symbol_news(
    symbol: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Return paginated news for a specific stock symbol, newest first."""
    clean_symbol = symbol.strip().upper()

    query = (
        db.query(NewsRecord)
        .filter(NewsRecord.symbol == clean_symbol)
        .order_by(NewsRecord.published_at.desc())
    )
    total = query.count()
    records = query.offset(offset).limit(limit).all()

    return NewsListResponse(
        items=records,
        pagination=PaginationMeta(total=total, limit=limit, offset=offset),
    )
