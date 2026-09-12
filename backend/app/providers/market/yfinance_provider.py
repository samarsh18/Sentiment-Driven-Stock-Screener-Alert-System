"""
backend/app/providers/market/yfinance_provider.py
--------------------------------------------------
YFinanceMarketDataProvider — yfinance implementation of MarketDataProvider.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Callable, List, Optional, Union

import pandas as pd
import yfinance as yf
from pydantic import ValidationError

from backend.app.models.market import MarketDataBar
from backend.app.providers.market.base import MarketDataProvider

logger = logging.getLogger(__name__)


def format_yahoo_symbol(symbol: str, exchange: str) -> str:
    """Format ticker symbol with Yahoo Finance exchange suffix."""
    clean_sym = symbol.strip().upper()
    clean_ex = exchange.strip().upper()

    if clean_ex == "NSE":
        if not clean_sym.endswith(".NS"):
            return f"{clean_sym}.NS"
        return clean_sym
    elif clean_ex == "BSE":
        if not clean_sym.endswith(".BO"):
            return f"{clean_sym}.BO"
        return clean_sym
    return clean_sym


def _default_download_fn(
    ticker_str: str,
    start: Optional[Union[datetime, date, str]],
    end: Optional[Union[datetime, date, str]],
    interval: str,
) -> pd.DataFrame:
    ticker = yf.Ticker(ticker_str)
    return ticker.history(start=start, end=end, interval=interval)


class YFinanceMarketDataProvider(MarketDataProvider):
    """
    MarketDataProvider implementation using Yahoo Finance (yfinance).
    """

    def __init__(
        self,
        download_fn: Optional[Callable[..., pd.DataFrame]] = None,
    ):
        self._download_fn = download_fn or _default_download_fn

    def get_historical_data(
        self,
        symbol: str,
        exchange: str = "NSE",
        start_date: Optional[Union[datetime, date, str]] = None,
        end_date: Optional[Union[datetime, date, str]] = None,
        interval: str = "1d",
    ) -> List[MarketDataBar]:
        if not isinstance(symbol, str) or not symbol.strip():
            return []

        clean_symbol = symbol.strip().upper()
        clean_exchange = exchange.strip().upper()
        yahoo_ticker = format_yahoo_symbol(clean_symbol, clean_exchange)

        try:
            df = self._download_fn(
                yahoo_ticker,
                start=start_date,
                end=end_date,
                interval=interval,
            )
        except Exception as exc:
            logger.warning(
                "yfinance download failed for ticker=%s: %s", yahoo_ticker, exc
            )
            return []

        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return []

        df = df.sort_index()

        bars: List[MarketDataBar] = []
        for idx, row in df.iterrows():
            bar = self._parse_row(idx, row, clean_symbol, clean_exchange)
            if bar is not None:
                bars.append(bar)

        return bars

    def _parse_row(
        self,
        timestamp_val: object,
        row: pd.Series,
        symbol: str,
        exchange: str,
    ) -> Optional[MarketDataBar]:
        try:
            open_val = float(row.get("Open"))
            high_val = float(row.get("High"))
            low_val = float(row.get("Low"))
            close_val = float(row.get("Close"))
            volume_val = float(row.get("Volume", 0.0))

            if (
                pd.isna(open_val)
                or pd.isna(high_val)
                or pd.isna(low_val)
                or pd.isna(close_val)
            ):
                return None

            if pd.isna(volume_val) or volume_val < 0:
                volume_val = 0.0

            if isinstance(timestamp_val, (pd.Timestamp, datetime)):
                dt = timestamp_val.to_pydatetime() if isinstance(timestamp_val, pd.Timestamp) else timestamp_val
            elif isinstance(timestamp_val, str):
                dt = datetime.fromisoformat(timestamp_val)
            else:
                return None

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)

            return MarketDataBar(
                symbol=symbol,
                exchange=exchange,
                timestamp=dt,
                open=open_val,
                high=high_val,
                low=low_val,
                close=close_val,
                volume=volume_val,
            )
        except (ValueError, TypeError, ValidationError):
            return None