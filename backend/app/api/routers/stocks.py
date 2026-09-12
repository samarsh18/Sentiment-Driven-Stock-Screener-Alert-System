"""
backend/app/api/routers/stocks.py
-----------------------------------
Stock endpoints.

GET /api/stocks/{symbol}/history    Paginated OHLCV history for a symbol
GET /api/stocks/{symbol}/news       (also in news.py — registered once in main.py)
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.api.schemas import PriceBarResponse, PricesListResponse
from backend.app.database.repository import get_market_data

router = APIRouter(prefix="/api/stocks", tags=["Stocks"])


@router.get("/{symbol}/history", response_model=PricesListResponse)
def get_price_history(
    symbol: str,
    exchange: str = Query("NSE", min_length=1, max_length=10),
    start: Optional[str] = Query(None, description="ISO-8601 start date (inclusive)"),
    end: Optional[str] = Query(None, description="ISO-8601 end date (inclusive)"),
    db: Session = Depends(get_db),
):
    """
    Return historical OHLCV bars for a stock symbol from the local database.

    Dates accept ISO-8601 strings, e.g. 2024-01-01 or 2024-01-01T00:00:00Z.
    """
    bars = get_market_data(
        db,
        symbol=symbol,
        exchange=exchange,
        start_date=start,
        end_date=end,
    )

    items = [
        PriceBarResponse(
            symbol=b.symbol,
            exchange=b.exchange,
            timestamp=b.timestamp,
            open=b.open,
            high=b.high,
            low=b.low,
            close=b.close,
            volume=b.volume,
        )
        for b in bars
    ]

    return PricesListResponse(
        symbol=symbol.strip().upper(),
        exchange=exchange.strip().upper(),
        items=items,
        total=len(items),
    )
