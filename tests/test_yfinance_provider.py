"""
tests/test_yfinance_provider.py
--------------------------------
Unit tests for YFinanceMarketDataProvider and MockMarketDataProvider.

Uses mock download functions so NO real network calls to Yahoo Finance are made.
"""

from datetime import datetime, timezone
import pandas as pd
import pytest

from backend.app.models.market import MarketDataBar
from backend.app.providers.market.base import MarketDataProvider
from backend.app.providers.market.mock_market import MockMarketDataProvider
from backend.app.providers.market.yfinance_provider import (
    YFinanceMarketDataProvider,
    format_yahoo_symbol,
)


def sample_df() -> pd.DataFrame:
    dates = pd.date_range(start="2024-04-01", periods=3, freq="D", tz="UTC")
    data = {
        "Open": [2500.0, 2510.0, 2520.0],
        "High": [2515.0, 2525.0, 2535.0],
        "Low": [2495.0, 2505.0, 2515.0],
        "Close": [2508.0, 2518.0, 2528.0],
        "Volume": [1000000.0, 1100000.0, 1200000.0],
    }
    return pd.DataFrame(data, index=dates)


class TestSymbolConversion:
    def test_nse_symbol_appends_suffix(self):
        assert format_yahoo_symbol("RELIANCE", "NSE") == "RELIANCE.NS"
        assert format_yahoo_symbol("tcs", "nse") == "TCS.NS"

    def test_nse_symbol_preserves_existing_suffix(self):
        assert format_yahoo_symbol("INFY.NS", "NSE") == "INFY.NS"

    def test_bse_symbol_appends_suffix(self):
        assert format_yahoo_symbol("RELIANCE", "BSE") == "RELIANCE.BO"
        assert format_yahoo_symbol("500325", "bse") == "500325.BO"

    def test_bse_symbol_preserves_existing_suffix(self):
        assert format_yahoo_symbol("500325.BO", "BSE") == "500325.BO"

    def test_other_exchange_leaves_symbol_as_is(self):
        assert format_yahoo_symbol("AAPL", "US") == "AAPL"


class TestYFinanceMarketDataProvider:
    def test_is_market_data_provider_subclass(self):
        assert issubclass(YFinanceMarketDataProvider, MarketDataProvider)
        assert isinstance(YFinanceMarketDataProvider(), MarketDataProvider)

    def test_successful_data_download_and_normalization(self):
        captured = {}

        def mock_download(ticker_str, start, end, interval):
            captured["ticker"] = ticker_str
            captured["start"] = start
            captured["end"] = end
            captured["interval"] = interval
            return sample_df()

        provider = YFinanceMarketDataProvider(download_fn=mock_download)
        bars = provider.get_historical_data(
            symbol="RELIANCE",
            exchange="NSE",
            start_date="2024-04-01",
            end_date="2024-04-03",
            interval="1d",
        )

        assert captured["ticker"] == "RELIANCE.NS"
        assert captured["interval"] == "1d"
        assert len(bars) == 3
        assert all(isinstance(bar, MarketDataBar) for bar in bars)

        first = bars[0]
        assert first.symbol == "RELIANCE"
        assert first.exchange == "NSE"
        assert first.open == 2500.0
        assert first.close == 2508.0
        assert first.timestamp.tzinfo == timezone.utc

    def test_chronological_ordering(self):
        df_rev = sample_df().sort_index(ascending=False)

        def mock_download(ticker_str, start, end, interval):
            return df_rev

        provider = YFinanceMarketDataProvider(download_fn=mock_download)
        bars = provider.get_historical_data("TCS", "NSE")

        assert len(bars) == 3
        assert bars[0].timestamp < bars[1].timestamp < bars[2].timestamp

    def test_missing_and_nan_values_ignored(self):
        dates = pd.date_range(start="2024-04-01", periods=3, freq="D", tz="UTC")
        data = {
            "Open": [2500.0, float("nan"), 2520.0],
            "High": [2515.0, 2525.0, float("nan")],
            "Low": [2495.0, 2505.0, 2515.0],
            "Close": [2508.0, 2518.0, 2528.0],
            "Volume": [1000000.0, 1100000.0, 1200000.0],
        }
        df_nan = pd.DataFrame(data, index=dates)

        provider = YFinanceMarketDataProvider(
            download_fn=lambda ticker, **kwargs: df_nan
        )
        bars = provider.get_historical_data("INFY", "NSE")

        assert len(bars) == 1
        assert bars[0].open == 2500.0

    def test_empty_dataframe_returns_empty_list(self):
        provider = YFinanceMarketDataProvider(
            download_fn=lambda ticker, **kwargs: pd.DataFrame()
        )
        bars = provider.get_historical_data("UNKNOWN", "NSE")
        assert bars == []

    def test_invalid_symbol_returns_empty_list(self):
        provider = YFinanceMarketDataProvider()
        assert provider.get_historical_data("") == []
        assert provider.get_historical_data("   ") == []

    def test_provider_error_handling(self):
        def crashing_download(ticker_str, **kwargs):
            raise RuntimeError("Network connection reset")

        provider = YFinanceMarketDataProvider(download_fn=crashing_download)
        bars = provider.get_historical_data("RELIANCE", "NSE")
        assert bars == []

    def test_timestamp_normalization_to_utc(self):
        dates = pd.date_range(start="2024-04-01", periods=2, freq="D")
        df_naive = pd.DataFrame(
            {
                "Open": [100.0, 101.0],
                "High": [105.0, 106.0],
                "Low": [99.0, 100.0],
                "Close": [102.0, 103.0],
                "Volume": [500.0, 600.0],
            },
            index=dates,
        )

        provider = YFinanceMarketDataProvider(
            download_fn=lambda ticker, **kwargs: df_naive
        )
        bars = provider.get_historical_data("TCS", "NSE")

        assert len(bars) == 2
        assert bars[0].timestamp.tzinfo == timezone.utc


class TestMockMarketDataProvider:
    def test_mock_provider_returns_deterministic_candles(self):
        provider = MockMarketDataProvider()
        bars = provider.get_historical_data("RELIANCE", "NSE")

        assert len(bars) == 5
        assert all(isinstance(b, MarketDataBar) for b in bars)
        assert bars[0].symbol == "RELIANCE"
        assert bars[0].exchange == "NSE"
        assert bars[0].open == 2500.0