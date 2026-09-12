"""
tests/test_event_study.py
--------------------------
Unit tests for historical event study service.

Tests are 100% offline and deterministic.
"""

from datetime import datetime, timedelta, timezone
import pytest

from backend.app.models.market import MarketDataBar
from backend.app.services.event_study import EventStudyResult, calculate_event_study


def make_daily_bars(
    symbol: str = "RELIANCE",
    prices: list[float] = None,
    start_dt: datetime = None,
) -> list[MarketDataBar]:
    if prices is None:
        prices = [100.0, 105.0, 110.0, 115.0, 120.0, 125.0]
    if start_dt is None:
        start_dt = datetime(2024, 4, 1, 9, 15, 0, tzinfo=timezone.utc)

    bars = []
    for i, p in enumerate(prices):
        bars.append(
            MarketDataBar(
                symbol=symbol,
                exchange="NSE",
                timestamp=start_dt + timedelta(days=i),
                open=p - 1.0,
                high=p + 2.0,
                low=p - 2.0,
                close=p,
                volume=10000.0,
            )
        )
    return bars


class TestEventStudy:
    def test_positive_reaction(self):
        bars = make_daily_bars(prices=[100.0, 105.0, 110.0, 115.0, 120.0, 125.0])
        pub_at = datetime(2024, 4, 1, 14, 0, 0, tzinfo=timezone.utc)

        res = calculate_event_study(
            news_id="N-POS",
            symbol="RELIANCE",
            exchange="NSE",
            published_at=pub_at,
            stock_prices=bars,
        )

        assert res.event_price == 100.0
        assert res.price_1d == 105.0
        assert res.price_3d == 115.0
        assert res.price_5d == 125.0
        assert res.return_1d == pytest.approx(0.05)
        assert res.return_3d == pytest.approx(0.15)
        assert res.return_5d == pytest.approx(0.25)
        assert res.benchmark_return_1d is None
        assert res.excess_return_1d is None

    def test_negative_reaction(self):
        bars = make_daily_bars(prices=[100.0, 95.0, 90.0, 85.0, 80.0, 75.0])
        pub_at = datetime(2024, 4, 1, 14, 0, 0, tzinfo=timezone.utc)

        res = calculate_event_study(
            news_id="N-NEG",
            symbol="TCS",
            exchange="NSE",
            published_at=pub_at,
            stock_prices=bars,
        )

        assert res.event_price == 100.0
        assert res.return_1d == pytest.approx(-0.05)
        assert res.return_3d == pytest.approx(-0.15)
        assert res.return_5d == pytest.approx(-0.25)

    def test_benchmark_adjustment(self):
        stock_bars = make_daily_bars(symbol="INFY", prices=[100.0, 110.0, 115.0, 120.0, 125.0, 130.0])
        bench_bars = make_daily_bars(symbol="NIFTY50", prices=[20000.0, 20400.0, 20600.0, 20800.0, 21000.0, 21200.0])
        pub_at = datetime(2024, 4, 1, 14, 0, 0, tzinfo=timezone.utc)

        res = calculate_event_study(
            news_id="N-BENCH",
            symbol="INFY",
            exchange="NSE",
            published_at=pub_at,
            stock_prices=stock_bars,
            benchmark_prices=bench_bars,
        )

        assert res.return_1d == pytest.approx(0.10)
        assert res.benchmark_return_1d == pytest.approx(0.02)
        assert res.excess_return_1d == pytest.approx(0.08)

    def test_weekend_event(self):
        dates = [
            datetime(2024, 4, 19, tzinfo=timezone.utc),  # Fri
            datetime(2024, 4, 22, tzinfo=timezone.utc),  # Mon
            datetime(2024, 4, 23, tzinfo=timezone.utc),  # Tue
            datetime(2024, 4, 24, tzinfo=timezone.utc),  # Wed
            datetime(2024, 4, 25, tzinfo=timezone.utc),  # Thu
            datetime(2024, 4, 26, tzinfo=timezone.utc),  # Fri
        ]
        prices = [100.0, 105.0, 108.0, 110.0, 112.0, 115.0]
        bars = [
            MarketDataBar(
                symbol="HDFCBANK",
                exchange="NSE",
                timestamp=d,
                open=p, high=p, low=p, close=p, volume=100.0
            )
            for d, p in zip(dates, prices)
        ]

        pub_at = datetime(2024, 4, 20, 14, 0, 0, tzinfo=timezone.utc)  # Sat

        res = calculate_event_study(
            news_id="N-WEEKEND",
            symbol="HDFCBANK",
            exchange="NSE",
            published_at=pub_at,
            stock_prices=bars,
        )

        assert res.event_price == 100.0
        assert res.price_1d == 105.0
        assert res.price_3d == 110.0
        assert res.price_5d == 115.0

    def test_market_holiday(self):
        dates = [
            datetime(2024, 4, 15, tzinfo=timezone.utc),
            datetime(2024, 4, 16, tzinfo=timezone.utc),
            datetime(2024, 4, 18, tzinfo=timezone.utc),
            datetime(2024, 4, 19, tzinfo=timezone.utc),
            datetime(2024, 4, 22, tzinfo=timezone.utc),
            datetime(2024, 4, 23, tzinfo=timezone.utc),
        ]
        prices = [100.0, 102.0, 106.0, 108.0, 110.0, 112.0]
        bars = [
            MarketDataBar(
                symbol="WIPRO", exchange="NSE", timestamp=d,
                open=p, high=p, low=p, close=p, volume=50.0
            )
            for d, p in zip(dates, prices)
        ]

        pub_at = datetime(2024, 4, 15, 18, 0, 0, tzinfo=timezone.utc)

        res = calculate_event_study(
            news_id="N-HOLIDAY",
            symbol="WIPRO",
            exchange="NSE",
            published_at=pub_at,
            stock_prices=bars,
        )

        assert res.event_price == 100.0
        assert res.price_1d == 102.0
        assert res.price_3d == 108.0
        assert res.price_5d == 112.0

    def test_insufficient_history(self):
        bars = make_daily_bars(prices=[100.0, 105.0, 110.0])
        pub_at = datetime(2024, 4, 1, 14, 0, 0, tzinfo=timezone.utc)

        res = calculate_event_study(
            news_id="N-SHORT",
            symbol="SBIN",
            exchange="NSE",
            published_at=pub_at,
            stock_prices=bars,
        )

        assert res.event_price == 100.0
        assert res.price_1d == 105.0
        assert res.return_1d == pytest.approx(0.05)
        assert res.price_3d is None
        assert res.return_3d is None
        assert res.price_5d is None
        assert res.return_5d is None

    def test_missing_benchmark(self):
        bars = make_daily_bars(prices=[100.0, 105.0, 110.0, 115.0, 120.0, 125.0])
        pub_at = datetime(2024, 4, 1, 14, 0, 0, tzinfo=timezone.utc)

        res = calculate_event_study(
            news_id="N-NOBENCH",
            symbol="TITAN",
            exchange="NSE",
            published_at=pub_at,
            stock_prices=bars,
            benchmark_prices=None,
        )

        assert res.return_1d == pytest.approx(0.05)
        assert res.benchmark_return_1d is None
        assert res.excess_return_1d is None

    def test_missing_pre_event_price(self):
        bars = make_daily_bars(start_dt=datetime(2024, 5, 1, tzinfo=timezone.utc))
        pub_at = datetime(2024, 4, 1, 14, 0, 0, tzinfo=timezone.utc)

        res = calculate_event_study(
            news_id="N-NOPRE",
            symbol="LTIM",
            exchange="NSE",
            published_at=pub_at,
            stock_prices=bars,
        )

        assert res.event_price is None
        assert res.return_1d is None
        assert res.return_3d is None
        assert res.return_5d is None

    def test_invalid_prices_handled(self):
        dates = [
            datetime(2024, 4, 1, tzinfo=timezone.utc),
            datetime(2024, 4, 2, tzinfo=timezone.utc),
            datetime(2024, 4, 3, tzinfo=timezone.utc),
        ]
        bars = [
            {"timestamp": dates[0], "close": 100.0},
            {"timestamp": dates[1], "close": -10.0},
            {"timestamp": dates[2], "close": 110.0},
        ]
        pub_at = datetime(2024, 4, 1, 14, 0, 0, tzinfo=timezone.utc)

        res = calculate_event_study(
            news_id="N-INVALID",
            symbol="AXISBANK",
            exchange="NSE",
            published_at=pub_at,
            stock_prices=bars,
        )

        assert res.event_price == 100.0
        assert res.price_1d == 110.0