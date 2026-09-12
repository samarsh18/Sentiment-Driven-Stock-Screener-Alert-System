"""
backend/app/api/routers/watchlist.py
--------------------------------------
Watchlist endpoints.

GET    /api/users/{user_id}/watchlist
POST   /api/users/{user_id}/watchlist
DELETE /api/users/{user_id}/watchlist/{symbol}
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, require_user
from backend.app.api.schemas import WatchlistItemCreate, WatchlistItemResponse, WatchlistResponse
from backend.app.database.repository import (
    add_watchlist_item,
    get_user_watchlist,
    remove_watchlist_item,
)

router = APIRouter(prefix="/api/users", tags=["Watchlist"])


@router.get("/{user_id}/watchlist", response_model=WatchlistResponse)
def get_watchlist(user=Depends(require_user), db: Session = Depends(get_db)):
    """Return all watchlist items for a user."""
    items = get_user_watchlist(db, user_id=user.id)
    return WatchlistResponse(items=items, total=len(items))


@router.post(
    "/{user_id}/watchlist",
    response_model=WatchlistItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_to_watchlist(
    body: WatchlistItemCreate,
    user=Depends(require_user),
    db: Session = Depends(get_db),
):
    """Add a stock to the user's watchlist."""
    item = add_watchlist_item(
        db, user_id=user.id, symbol=body.symbol, company_name=body.company_name
    )
    return item


@router.delete(
    "/{user_id}/watchlist/{symbol}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_from_watchlist(
    symbol: str,
    user=Depends(require_user),
    db: Session = Depends(get_db),
):
    """Remove a stock from the user's watchlist. Returns 404 if not found."""
    removed = remove_watchlist_item(db, user_id=user.id, symbol=symbol)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Symbol {symbol.upper()!r} not found in watchlist.",
        )
