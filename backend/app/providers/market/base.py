"""
backend/app/providers/market/base.py
------------------------------------
Abstract base class defining the MarketDataProvider interface.
"""

from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import List, Optional, Union

from backend.app.models.market import MarketDataBar


class MarketDataProvider(ABC):
    """Abstract interface for historical market data providers."""

    @abstractmethod
    def get_historical_data(
        self,
        symbol: str,
        exchange: str = "NSE",
        start_date: Optional[Union[datetime, date, str]] = None,
        end_date: Optional[Union[datetime, date, str]] = None,
        interval: str = "1d",
    ) -> List[MarketDataBar]:
        """
        Fetch historical OHLCV market data for a stock symbol.

        Parameters
        ----------
        symbol : str
            Stock ticker symbol (e.g. "RELIANCE", "TCS").
        exchange : str, optional
            Exchange name ("NSE", "BSE", etc.). Defaults to "NSE".
        start_date : Union[datetime, date, str], optional
            Start date for historical data range.
        end_date : Union[datetime, date, str], optional
            End date for historical data range.
        interval : str, optional
            Data interval (e.g. "1d", "1wk", "1mo"). Defaults to "1d".

        Returns
        -------
        List[MarketDataBar]
            Chronologically ordered list of normalized MarketDataBar objects.
        """
        ...