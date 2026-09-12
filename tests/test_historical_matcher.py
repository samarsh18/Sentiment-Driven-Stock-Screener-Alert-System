"""
tests/test_historical_matcher.py
---------------------------------
Unit tests for Historical Event Matcher service.

All tests are 100% offline and deterministic.
"""

import pytest

from backend.app.services.historical_matcher import (
    HistoricalEventFeatures,
    HistoricalEventMatcher,
    HistoricalMatchResult,
    match_historical_events,
)


def make_event(
    news_id: str,
    symbol: str = "TATAMOTORS",
    event_type: str = "MAJOR_CONTRACT",
    sentiment: str = "positive",
    sector: str = "AUTOMOBILE",
    market_cap_bucket: str = "LARGE",
) -> HistoricalEventFeatures:
    return HistoricalEventFeatures(
        news_id=news_id,
        symbol=symbol,
        event_type=event_type,
        sentiment=sentiment,
        sector=sector,
        market_cap_bucket=market_cap_bucket,
    )


class TestHistoricalMatcher:
    def test_exact_tier_1_match(self):
        target = make_event("T-1", "TATAMOTORS", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "LARGE")

        history = [
            make_event(f"H-{i}", "MARUTI", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "LARGE")
            for i in range(10)
        ]

        result = match_historical_events(target, history, min_sample_size=5)

        assert result.match_tier == 1
        assert result.sample_size == 10
        assert result.sufficient_sample is True
        assert len(result.matched_events) == 10
        assert "Tier 1" in result.match_reason

    def test_tier_2_fallback(self):
        target = make_event("T-1", "TATAMOTORS", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "LARGE")

        # 2 events match Tier 1 (LARGE), 8 events match Tier 2 (MID)
        history = [
            make_event(f"H1-{i}", "M&M", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "LARGE") for i in range(2)
        ] + [
            make_event(f"H2-{i}", "BAJAJ-AUTO", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "MID") for i in range(8)
        ]

        result = match_historical_events(target, history, min_sample_size=5)

        assert result.match_tier == 2
        assert result.sample_size == 10
        assert result.sufficient_sample is True

    def test_tier_3_fallback(self):
        target = make_event("T-1", "TATAMOTORS", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "LARGE")

        # Tier 1: 1 match, Tier 2: 1 match (total 2 Tier 3+ matches), Tier 3: 8 matches (IT sector instead of AUTOMOBILE)
        history = [
            make_event("H1", "M&M", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "LARGE"),
            make_event("H2", "BAJAJ-AUTO", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "MID"),
        ] + [
            make_event(f"H3-{i}", "INFY", "MAJOR_CONTRACT", "positive", "IT", "LARGE") for i in range(8)
        ]

        result = match_historical_events(target, history, min_sample_size=5)

        assert result.match_tier == 3
        assert result.sample_size == 10
        assert result.sufficient_sample is True

    def test_tier_4_fallback(self):
        target = make_event("T-1", "TATAMOTORS", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "LARGE")

        # Tier 1-3: 2 positive matches, Tier 4: 8 negative matches (different sentiment)
        history = [
            make_event(f"H1-{i}", "M&M", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "LARGE") for i in range(2)
        ] + [
            make_event(f"H4-{i}", "TCS", "MAJOR_CONTRACT", "negative", "IT", "LARGE") for i in range(8)
        ]

        result = match_historical_events(target, history, min_sample_size=5)

        assert result.match_tier == 4
        assert result.sample_size == 10
        assert result.sufficient_sample is True

    def test_no_matches(self):
        target = make_event("T-1", "TATAMOTORS", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "LARGE")
        history = [
            make_event(f"H-{i}", "RELIANCE", "EARNINGS_RELEASE", "positive", "ENERGY", "LARGE") for i in range(10)
        ]

        result = match_historical_events(target, history, min_sample_size=5)

        assert result.match_tier == 0
        assert result.sample_size == 0
        assert result.sufficient_sample is False
        assert len(result.matched_events) == 0

    def test_sample_size_threshold(self):
        target = make_event("T-1", "TATAMOTORS", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "LARGE")
        history = [
            make_event(f"H-{i}", "MARUTI", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "LARGE") for i in range(3)
        ]

        # min_sample_size = 5 -> fails threshold, returns Tier 4 fallback with sufficient_sample=False
        result = match_historical_events(target, history, min_sample_size=5)
        assert result.sample_size == 3
        assert result.sufficient_sample is False
        assert result.match_tier == 4

        # min_sample_size = 3 -> meets threshold
        result_met = match_historical_events(target, history, min_sample_size=3)
        assert result_met.sample_size == 3
        assert result_met.sufficient_sample is True
        assert result_met.match_tier == 1

    def test_max_sample_size_limit(self):
        target = make_event("T-1", "TATAMOTORS", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "LARGE")
        history = [
            make_event(f"H-{i}", "MARUTI", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "LARGE") for i in range(50)
        ]

        result = match_historical_events(target, history, min_sample_size=5, max_sample_size=10)

        assert result.sample_size == 10
        assert len(result.matched_events) == 10
        assert result.sufficient_sample is True

    def test_same_event_type_different_stock(self):
        target = make_event("T-1", "TATAMOTORS", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "LARGE")
        history = [
            make_event("H-1", "MARUTI", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "LARGE"),
            make_event("H-2", "M&M", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "LARGE"),
            make_event("H-3", "HEROMOTOCO", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "LARGE"),
        ]

        result = match_historical_events(target, history, min_sample_size=2)

        symbols = {e.symbol for e in result.matched_events}
        assert "TATAMOTORS" not in symbols
        assert symbols == {"MARUTI", "M&M", "HEROMOTOCO"}

    def test_duplicate_ids_removed(self):
        target = make_event("T-1", "TATAMOTORS", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "LARGE")
        history = [
            make_event("H-DUP", "MARUTI", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "LARGE"),
            make_event("H-DUP", "MARUTI", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "LARGE"),
            make_event("H-UNIQUE", "M&M", "MAJOR_CONTRACT", "positive", "AUTOMOBILE", "LARGE"),
        ]

        result = match_historical_events(target, history, min_sample_size=1)

        assert result.sample_size == 2
        matched_ids = [e.news_id for e in result.matched_events]
        assert matched_ids == ["H-DUP", "H-UNIQUE"]

    def test_missing_optional_metadata(self):
        target = HistoricalEventFeatures(news_id="T-MISSING", symbol="WIPRO", event_type="MAJOR_CONTRACT")
        history = [
            HistoricalEventFeatures(news_id="H-1", symbol="INFY", event_type="MAJOR_CONTRACT"),
            HistoricalEventFeatures(news_id="H-2", symbol="TCS", event_type="MAJOR_CONTRACT"),
        ]

        result = match_historical_events(target, history, min_sample_size=2)

        assert result.match_tier == 1
        assert result.sample_size == 2
        assert result.sufficient_sample is True
