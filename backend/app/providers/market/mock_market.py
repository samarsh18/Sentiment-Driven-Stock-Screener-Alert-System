"""
backend/app/providers/market/mock_market.py
--------------------------------------------
MockMarketDataProvider — deterministic in-memory market data provider for testing.
"""

from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Union

from backend.app.models.market import MarketDataBar
from backend.app.providers.market.base import MarketDataProvider


class MockMarketDataProvider(MarketDataProvider):
    """
    Deterministic in-memory market data provider for development and testing.
    """

    def get_historical_data(
        self,
        symbol: str,
        exchange: str = "NSE",
        start_date: Optional[Union[datetime, date, str]] = None,
        end_date: Optional[Union[datetime, date, str]] = None,
        interval: str = "1d",
    ) -> List[MarketDataBar]:
        if not symbol or not symbol.strip():
            return []

        clean_symbol = symbol.strip().upper()
        clean_exchange = exchange.strip().upper()

        base_time = datetime(2024, 4, 1, 9, 15, 0, tzinfo=timezone.utc)
        base_price = 2500.0

        bars: List[MarketDataBar] = []
        for i in range(5):
            bar_time = base_time + timedelta(days=i)
            bar = MarketDataBar(
                symbol=clean_symbol,
                exchange=clean_exchange,
                timestamp=bar_time,
                open=base_price + i * 10,
                high=base_price + i * 10 + 15,
                low=base_price + i * 10 - 5,
                close=base_price + i * 10 + 8,
                volume=1000000.0 + i * 50000,
            )
            bars.append(bar)

        return bars