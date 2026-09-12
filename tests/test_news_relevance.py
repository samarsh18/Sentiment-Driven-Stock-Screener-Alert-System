"""
tests/test_news_relevance.py
-----------------------------
Unit tests for News Relevance Filter & News Deduplication service.

All tests are 100% offline and deterministic.
"""

from datetime import datetime, timezone
import pytest

from backend.app.models.news import NewsItem
from backend.app.services.news_relevance import (
    NewsRelevanceFilter,
    RelevanceResult,
    StockMetadata,
    deduplicate_news,
    evaluate_relevance,
    filter_relevant_news,
)


def make_news(
    news_id: str,
    symbol: str = "TCS",
    company_name: str = "Tata Consultancy Services",
    title: str = "TCS announces new cloud partnership",
    content: str = "Tata Consultancy Services has expanded its global partnership.",
    url: str = "https://example.com/news/1",
    published_at: datetime = None,
) -> NewsItem:
    if published_at is None:
        published_at = datetime(2024, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
    return NewsItem(
        news_id=news_id,
        symbol=symbol,
        company_name=company_name,
        title=title,
        content=content,
        source="GDELT",
        url=url,
        published_at=published_at,
    )


def make_meta(
    symbol: str = "TCS",
    company_name: str = "Tata Consultancy Services",
    aliases: list[str] = None,
    sector: str = "IT",
) -> StockMetadata:
    if aliases is None:
        aliases = ["TCS Ltd", "Tata Consultancy"]
    return StockMetadata(
        symbol=symbol,
        company_name=company_name,
        aliases=aliases,
        sector=sector,
    )


class TestNewsRelevance:
    def test_exact_company_title_match(self):
        meta = make_meta()
        item = make_news(
            news_id="N-1",
            title="Tata Consultancy Services reports Q4 profit growth",
            content="Revenue grew significantly in NSE trading.",
        )
        res = evaluate_relevance(item, meta, threshold=5)

        assert res.relevant is True
        assert res.score >= 5
        assert "exact_company_name_in_title" in res.matched_signals

    def test_exact_company_content_match(self):
        meta = make_meta()
        item = make_news(
            news_id="N-2",
            title="IT Sector Update: Key earnings ahead",
            content="Tata Consultancy Services is expected to report strong performance in INR.",
        )
        res = evaluate_relevance(item, meta, threshold=3)

        assert res.relevant is True
        assert "exact_company_name_in_content" in res.matched_signals

    def test_ticker_title_match(self):
        meta = make_meta()
        item = make_news(
            news_id="N-3",
            title="TCS signs multi-million dollar IT contract",
            content="The Indian tech giant registered strong gains.",
        )
        res = evaluate_relevance(item, meta, threshold=4)

        assert res.relevant is True
        assert "exact_ticker_in_title" in res.matched_signals

    def test_ticker_content_match(self):
        meta = make_meta()
        item = make_news(
            news_id="N-4",
            title="Global Software Trends",
            content="Companies like TCS are expanding in NSE markets.",
        )
        res = evaluate_relevance(item, meta, threshold=3)

        assert res.relevant is True
        assert "exact_ticker_in_content" in res.matched_signals

    def test_alias_match(self):
        meta = make_meta(aliases=["Tata Consultancy"])
        item = make_news(
            news_id="N-5",
            title="Tata Consultancy expands European operations",
            content="The firm hired 500 engineers.",
        )
        res = evaluate_relevance(item, meta, threshold=4)

        assert res.relevant is True
        assert "known_alias_in_title" in res.matched_signals

    def test_ticker_false_positive(self):
        # Short ticker TCS in content alone without company name or alias -> score 2 < threshold 5
        meta = make_meta(symbol="TCS", company_name="Tata Consultancy Services", aliases=[])
        item = make_news(
            news_id="N-6",
            title="Market Statistics and Analytical Techniques",
            content="We used tcs algorithms to calculate data.",
        )
        res = evaluate_relevance(item, meta, threshold=5)

        assert res.relevant is False
        assert res.score < 5

    def test_irrelevant_article(self):
        meta = make_meta(symbol="RELIANCE", company_name="Reliance Industries")
        item = make_news(
            news_id="N-7",
            title="Unrelated Pharmaceutical Breakthrough in US",
            content="A medical laboratory discovered a new molecule in New York.",
        )
        res = evaluate_relevance(item, meta, threshold=5)

        assert res.relevant is False
        assert res.score == 0

    def test_multiple_matching_signals(self):
        meta = make_meta()
        item = make_news(
            news_id="N-8",
            title="TCS: Tata Consultancy Services Q4 Results on NSE",
            content="Tata Consultancy Services reported high profits in INR.",
        )
        res = evaluate_relevance(item, meta, threshold=5)

        assert res.relevant is True
        assert res.score >= 10
        assert len(res.matched_signals) >= 3

    def test_case_insensitive_matching(self):
        meta = make_meta(symbol="TCS", company_name="Tata Consultancy Services")
        item = make_news(
            news_id="N-9",
            title="tata consultancy services wins contract",
            content="tcs announced new features.",
        )
        res = evaluate_relevance(item, meta, threshold=5)

        assert res.relevant is True
        assert "exact_company_name_in_title" in res.matched_signals

    def test_punctuation_normalization(self):
        meta = make_meta(symbol="TCS", company_name="Tata Consultancy Services")
        item = make_news(
            news_id="N-10",
            title="Tata Consultancy Services: Q4 Results!",
            content="Tata Consultancy Services, Ltd. reported profits.",
        )
        res = evaluate_relevance(item, meta, threshold=5)

        assert res.relevant is True

    def test_threshold_behavior(self):
        meta = StockMetadata(symbol="WIPRO", company_name="Wipro Limited")
        item = make_news(
            news_id="N-11",
            symbol="WIPRO",
            company_name="Wipro Limited",
            title="Software Industry Outlook",
            content="Wipro expands rapidly.",
        )
        res_default = evaluate_relevance(item, meta, threshold=5)
        res_low_thresh = evaluate_relevance(item, meta, threshold=2)

        assert res_default.relevant is False
        assert res_low_thresh.relevant is True

    def test_missing_optional_metadata(self):
        meta = StockMetadata(symbol="INFY", company_name="Infosys")
        item = make_news(
            news_id="N-12",
            symbol="INFY",
            company_name="Infosys",
            title="Infosys announces share buyback",
            content="Infosys board approved buyback.",
        )
        res = evaluate_relevance(item, meta, threshold=5)

        assert res.relevant is True


class TestNewsDeduplication:
    def test_duplicate_news_id(self):
        item1 = make_news(news_id="DUP-ID", title="Title A", url="http://ex.com/a")
        item2 = make_news(news_id="DUP-ID", title="Title B", url="http://ex.com/b")

        deduped = deduplicate_news([item1, item2])
        assert len(deduped) == 1
        assert deduped[0].news_id == "DUP-ID"

    def test_duplicate_url(self):
        item1 = make_news(news_id="N-1", title="Title 1", url="https://example.com/article/1/")
        item2 = make_news(news_id="N-2", title="Title 2", url="http://example.com/article/1")

        deduped = deduplicate_news([item1, item2])
        assert len(deduped) == 1

    def test_duplicate_normalized_title(self):
        item1 = make_news(news_id="N-1", title="Tata Motors quarterly profit jumps 50%", url="http://ex.com/1")
        item2 = make_news(news_id="N-2", title="Tata Motors quarterly profit jumps 50 percent!", url="http://ex.com/2")

        deduped = deduplicate_news([item1, item2])
        assert len(deduped) == 1

    def test_similar_but_meaningfully_different_titles_retained(self):
        item1 = make_news(news_id="N-1", title="Tata Motors quarterly profit jumps 50%", url="http://ex.com/1")
        item2 = make_news(news_id="N-2", title="Tata Motors launches new EV commercial truck line", url="http://ex.com/2")

        deduped = deduplicate_news([item1, item2])
        assert len(deduped) == 2

    def test_different_companies_retained(self):
        item1 = make_news(news_id="N-1", symbol="TCS", company_name="TCS", title="TCS Q4 profit jumps 15%", url="https://example.com/tcs")
        item2 = make_news(news_id="N-2", symbol="INFY", company_name="Infosys", title="Infosys Q4 profit jumps 15%", url="https://example.com/infy")

        deduped = deduplicate_news([item1, item2])
        assert len(deduped) == 2

    def test_ordering(self):
        t1 = datetime(2024, 4, 1, 10, 0, tzinfo=timezone.utc)
        t2 = datetime(2024, 4, 1, 9, 0, tzinfo=timezone.utc)

        item1 = make_news(news_id="N-1", title="Duplicate Title Here", url="http://ex.com/1", published_at=t1)
        item2 = make_news(news_id="N-2", title="Duplicate Title Here", url="http://ex.com/2", published_at=t2)

        # Earliest published_at (item2) should be chosen as representative
        deduped = deduplicate_news([item1, item2])
        assert len(deduped) == 1
        assert deduped[0].news_id == "N-2"

    def test_empty_input(self):
        deduped = deduplicate_news([])
        assert deduped == []
