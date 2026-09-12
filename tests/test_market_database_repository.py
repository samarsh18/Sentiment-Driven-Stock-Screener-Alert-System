"""
tests/test_market_database_repository.py
-----------------------------------------
Unit tests for MarketDataBar database persistence and querying functions.

Uses an in-memory SQLite database so tests are 100% offline and isolated.
"""

from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database.config import init_db
from backend.app.database.repository import get_market_data, save_market_data
from backend.app.models.market import MarketDataBar


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    init_db(target_engine=engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


def make_bar(
    symbol: str = "RELIANCE",
    exchange: str = "NSE",
    days_offset: int = 0,
    price_base: float = 2500.0,
) -> MarketDataBar:
    base_dt = datetime(2024, 4, 1, 9, 15, 0, tzinfo=timezone.utc)
    return MarketDataBar(
        symbol=symbol,
        exchange=exchange,
        timestamp=base_dt + timedelta(days=days_offset),
        open=price_base + days_offset * 10,
        high=price_base + days_offset * 10 + 15,
        low=price_base + days_offset * 10 - 5,
        close=price_base + days_offset * 10 + 8,
        volume=1000000.0 + days_offset * 50000,
    )


class TestMarketDatabaseRepository:
    def test_insert_one_candle(self, db_session):
        bar = make_bar()
        count = save_market_data(db_session, [bar])
        assert count == 1

        retrieved = get_market_data(db_session, "RELIANCE", "NSE")
        assert len(retrieved) == 1
        assert retrieved[0].symbol == "RELIANCE"
        assert retrieved[0].exchange == "NSE"

    def test_insert_multiple_candles(self, db_session):
        bars = [make_bar(days_offset=i) for i in range(3)]
        count = save_market_data(db_session, bars)
        assert count == 3

        retrieved = get_market_data(db_session, "RELIANCE", "NSE")
        assert len(retrieved) == 3

    def test_values_round_trip_correctly(self, db_session):
        bar = make_bar()
        save_market_data(db_session, [bar])

        retrieved = get_market_data(db_session, "RELIANCE", "NSE")
        r = retrieved[0]

        assert r.symbol == bar.symbol
        assert r.exchange == bar.exchange
        assert r.open == pytest.approx(bar.open)
        assert r.high == pytest.approx(bar.high)
        assert r.low == pytest.approx(bar.low)
        assert r.close == pytest.approx(bar.close)
        assert r.volume == pytest.approx(bar.volume)
        assert r.timestamp == bar.timestamp

    def test_retrieve_by_symbol(self, db_session):
        save_market_data(db_session, [make_bar(symbol="TCS")])
        save_market_data(db_session, [make_bar(symbol="INFY")])

        tcs_bars = get_market_data(db_session, "TCS")
        assert len(tcs_bars) == 1
        assert tcs_bars[0].symbol == "TCS"

        infy_bars = get_market_data(db_session, "INFY")
        assert len(infy_bars) == 1
        assert infy_bars[0].symbol == "INFY"

    def test_retrieve_within_date_range(self, db_session):
        bars = [make_bar(days_offset=i) for i in range(5)]
        save_market_data(db_session, bars)

        start = datetime(2024, 4, 2, tzinfo=timezone.utc)
        end = datetime(2024, 4, 4, 23, 59, 59, tzinfo=timezone.utc)

        filtered = get_market_data(db_session, "RELIANCE", "NSE", start_date=start, end_date=end)
        assert len(filtered) == 3
        timestamps = [b.timestamp for b in filtered]
        assert min(timestamps) >= start
        assert max(timestamps) <= end

    def test_duplicate_insertion_does_not_duplicate_rows(self, db_session):
        bar = make_bar()
        count1 = save_market_data(db_session, [bar])
        count2 = save_market_data(db_session, [bar])

        assert count1 == 1
        assert count2 == 0

        retrieved = get_market_data(db_session, "RELIANCE", "NSE")
        assert len(retrieved) == 1

    def test_multiple_symbols_remain_isolated(self, db_session):
        save_market_data(db_session, [make_bar(symbol="AAPL")])
        save_market_data(db_session, [make_bar(symbol="MSFT")])

        aapl = get_market_data(db_session, "AAPL")
        msft = get_market_data(db_session, "MSFT")

        assert len(aapl) == 1
        assert len(msft) == 1
        assert aapl[0].symbol == "AAPL"
        assert msft[0].symbol == "MSFT"

    def test_multiple_exchanges_remain_isolated(self, db_session):
        bar_nse = make_bar(symbol="RELIANCE", exchange="NSE")
        bar_bse = make_bar(symbol="RELIANCE", exchange="BSE")

        save_market_data(db_session, [bar_nse, bar_bse])

        nse_bars = get_market_data(db_session, "RELIANCE", "NSE")
        bse_bars = get_market_data(db_session, "RELIANCE", "BSE")

        assert len(nse_bars) == 1
        assert nse_bars[0].exchange == "NSE"
        assert len(bse_bars) == 1
        assert bse_bars[0].exchange == "BSE"

    def test_empty_result_for_unknown_symbol(self, db_session):
        bars = get_market_data(db_session, "NONEXISTENT", "NSE")
        assert bars == []