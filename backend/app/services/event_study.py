"""
backend/app/services/event_study.py
-----------------------------------
Historical Event Study Service.

Calculates stock price returns and benchmark excess returns over 1, 3, and 5
TRADING days relative to a news publication timestamp.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, List, Optional, Union

from pydantic import BaseModel, Field

from backend.app.models.market import MarketDataBar

logger = logging.getLogger(__name__)


class EventStudyResult(BaseModel):
    """
    Result of a historical event study analysis.
    """

    news_id: str
    symbol: str
    exchange: str
    event_date: datetime
    event_price: Optional[float] = None

    price_1d: Optional[float] = None
    price_3d: Optional[float] = None
    price_5d: Optional[float] = None

    return_1d: Optional[float] = None
    return_3d: Optional[float] = None
    return_5d: Optional[float] = None

    benchmark_return_1d: Optional[float] = None
    benchmark_return_3d: Optional[float] = None
    benchmark_return_5d: Optional[float] = None

    excess_return_1d: Optional[float] = None
    excess_return_3d: Optional[float] = None
    excess_return_5d: Optional[float] = None

    model_config = {
        "extra": "forbid",
        "arbitrary_types_allowed": True,
    }


def _get_dt(val: Any) -> Optional[datetime]:
    """Extract a UTC-aware datetime from a bar object, ORM model, datetime, date, or string."""
    if val is None:
        return None

    dt: Optional[datetime] = None

    if isinstance(val, datetime):
        dt = val
    elif isinstance(val, date):
        dt = datetime.combine(val, datetime.min.time())
    elif isinstance(val, str):
        try:
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
        except ValueError:
            return None
    elif hasattr(val, "timestamp") and not callable(getattr(val, "timestamp")):
        raw = getattr(val, "timestamp")
        return _get_dt(raw)
    elif isinstance(val, dict):
        raw = val.get("timestamp")
        return _get_dt(raw)
    else:
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _get_close(bar: Any) -> Optional[float]:
    """Extract close price as a valid positive float."""
    if hasattr(bar, "close"):
        val = bar.close
    elif isinstance(bar, dict):
        val = bar.get("close")
    else:
        val = None

    try:
        fval = float(val)
        if fval > 0:
            return fval
    except (TypeError, ValueError):
        pass
    return None


def calculate_event_study(
    news_id: str,
    symbol: str,
    exchange: str,
    published_at: Union[datetime, date, str],
    stock_prices: List[Any],
    benchmark_prices: Optional[List[Any]] = None,
) -> EventStudyResult:
    """
    Calculate 1-, 3-, and 5-trading day returns and benchmark excess returns.

    Parameters
    ----------
    news_id : str
        Unique news item identifier.
    symbol : str
        Stock ticker symbol.
    exchange : str
        Stock exchange (e.g. "NSE", "BSE").
    published_at : Union[datetime, date, str]
        News publication timestamp.
    stock_prices : List[Any]
        List of historical price bars for the stock.
    benchmark_prices : Optional[List[Any]], optional
        List of historical price bars for the benchmark (e.g. NIFTY 50).

    Returns
    -------
    EventStudyResult
        Calculated event study returns and excess returns.
    """
    clean_symbol = symbol.strip().upper() if isinstance(symbol, str) else ""
    clean_exchange = exchange.strip().upper() if isinstance(exchange, str) else "NSE"

    event_dt = _get_dt(published_at)
    if event_dt is None:
        event_dt = datetime.now(timezone.utc)

    # Process and sort stock prices
    valid_stock_bars = []
    for bar in stock_prices or []:
        dt = _get_dt(bar)
        close = _get_close(bar)
        if dt is not None and close is not None:
            valid_stock_bars.append((dt, close))

    valid_stock_bars.sort(key=lambda x: x[0])

    # Find last trading day on or before published_at
    event_idx = -1
    for i, (dt, close) in enumerate(valid_stock_bars):
        if dt.date() <= event_dt.date():
            event_idx = i
        else:
            break

    if event_idx == -1:
        return EventStudyResult(
            news_id=news_id,
            symbol=clean_symbol,
            exchange=clean_exchange,
            event_date=event_dt,
            event_price=None,
        )

    event_price = valid_stock_bars[event_idx][1]

    # Trading day post-event prices
    price_1d = valid_stock_bars[event_idx + 1][1] if event_idx + 1 < len(valid_stock_bars) else None
    price_3d = valid_stock_bars[event_idx + 3][1] if event_idx + 3 < len(valid_stock_bars) else None
    price_5d = valid_stock_bars[event_idx + 5][1] if event_idx + 5 < len(valid_stock_bars) else None

    # Stock returns
    return_1d = round((price_1d / event_price) - 1.0, 6) if price_1d is not None else None
    return_3d = round((price_3d / event_price) - 1.0, 6) if price_3d is not None else None
    return_5d = round((price_5d / event_price) - 1.0, 6) if price_5d is not None else None

    # Benchmark returns calculation
    bench_return_1d = None
    bench_return_3d = None
    bench_return_5d = None

    if benchmark_prices:
        valid_bench_bars = []
        for bar in benchmark_prices:
            dt = _get_dt(bar)
            close = _get_close(bar)
            if dt is not None and close is not None:
                valid_bench_bars.append((dt, close))

        valid_bench_bars.sort(key=lambda x: x[0])

        bench_idx = -1
        for i, (dt, close) in enumerate(valid_bench_bars):
            if dt.date() <= event_dt.date():
                bench_idx = i
            else:
                break

        if bench_idx != -1:
            bench_event_price = valid_bench_bars[bench_idx][1]
            b_price_1d = valid_bench_bars[bench_idx + 1][1] if bench_idx + 1 < len(valid_bench_bars) else None
            b_price_3d = valid_bench_bars[bench_idx + 3][1] if bench_idx + 3 < len(valid_bench_bars) else None
            b_price_5d = valid_bench_bars[bench_idx + 5][1] if bench_idx + 5 < len(valid_bench_bars) else None

            if b_price_1d is not None:
                bench_return_1d = round((b_price_1d / bench_event_price) - 1.0, 6)
            if b_price_3d is not None:
                bench_return_3d = round((b_price_3d / bench_event_price) - 1.0, 6)
            if b_price_5d is not None:
                bench_return_5d = round((b_price_5d / bench_event_price) - 1.0, 6)

    # Excess returns
    excess_return_1d = round(return_1d - bench_return_1d, 6) if return_1d is not None and bench_return_1d is not None else None
    excess_return_3d = round(return_3d - bench_return_3d, 6) if return_3d is not None and bench_return_3d is not None else None
    excess_return_5d = round(return_5d - bench_return_5d, 6) if return_5d is not None and bench_return_5d is not None else None

    return EventStudyResult(
        news_id=news_id,
        symbol=clean_symbol,
        exchange=clean_exchange,
        event_date=event_dt,
        event_price=event_price,
        price_1d=price_1d,
        price_3d=price_3d,
        price_5d=price_5d,
        return_1d=return_1d,
        return_3d=return_3d,
        return_5d=return_5d,
        benchmark_return_1d=bench_return_1d,
        benchmark_return_3d=bench_return_3d,
        benchmark_return_5d=bench_return_5d,
        excess_return_1d=excess_return_1d,
        excess_return_3d=excess_return_3d,
        excess_return_5d=excess_return_5d,
    )