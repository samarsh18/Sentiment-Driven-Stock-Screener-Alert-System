"""
tests/test_news_provider.py
---------------------------
Unit tests for the NewsProvider interface and MockNewsProvider.

Coverage:
  1.  MockNewsProvider can be instantiated.
  2.  fetch_news returns a list.
  3.  Returned objects are NewsItem instances.
  4.  symbol is normalised to uppercase in every returned item.
  5.  company_name is populated in every returned item.
  6.  title is non-empty in every returned item.
  7.  content is non-empty in every returned item.
  8.  source is non-empty in every returned item.
  9.  url is non-empty in every returned item.
  10. published_at is a datetime in every returned item.
  11. limit parameter is respected (fewer items returned).
  12. limit=1 returns exactly one item.
  13. limit=0 returns an empty list.
  14. limit larger than corpus returns all corpus items.
  15. All returned NewsItems pass Pydantic validation (round-trip).
  16. MockNewsProvider is usable polymorphically as a NewsProvider.
  17. Different symbols produce items tagged with that symbol.
  18. news_id is non-empty and unique within a single result set.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from backend.app.models.news import NewsItem
from backend.app.providers.base import NewsProvider
from backend.app.providers.mock import MockNewsProvider, _MOCK_CORPUS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def provider() -> MockNewsProvider:
    return MockNewsProvider()


@pytest.fixture()
def default_items(provider: MockNewsProvider) -> list[NewsItem]:
    """Default fetch — uses AAPL as a representative ticker."""
    return provider.fetch_news("AAPL", "Apple Inc.")


# ---------------------------------------------------------------------------
# 1. Instantiation
# ---------------------------------------------------------------------------

class TestInstantiation:
    def test_can_be_instantiated(self):
        p = MockNewsProvider()
        assert p is not None

    def test_is_news_provider_subclass(self):
        assert issubclass(MockNewsProvider, NewsProvider)

    def test_instance_is_news_provider(self, provider):
        assert isinstance(provider, NewsProvider)


# ---------------------------------------------------------------------------
# 2 & 3. Return type
# ---------------------------------------------------------------------------

class TestReturnType:
    def test_returns_a_list(self, default_items):
        assert isinstance(default_items, list)

    def test_list_is_not_empty_by_default(self, default_items):
        assert len(default_items) > 0

    def test_every_item_is_news_item(self, default_items):
        for item in default_items:
            assert isinstance(item, NewsItem), (
                f"Expected NewsItem, got {type(item)}"
            )


# ---------------------------------------------------------------------------
# 4. Symbol normalisation
# ---------------------------------------------------------------------------

class TestSymbolNormalisation:
    def test_uppercase_symbol_in_results(self, provider):
        items = provider.fetch_news("aapl", "Apple Inc.")
        for item in items:
            assert item.symbol == "AAPL"

    def test_mixed_case_symbol_normalised(self, provider):
        items = provider.fetch_news("mSfT", "Microsoft Corporation")
        for item in items:
            assert item.symbol == "MSFT"

    def test_already_uppercase_unchanged(self, provider):
        items = provider.fetch_news("TSLA", "Tesla Inc.")
        for item in items:
            assert item.symbol == "TSLA"


# ---------------------------------------------------------------------------
# 5–10. Field population
# ---------------------------------------------------------------------------

class TestFieldPopulation:
    def test_company_name_populated(self, default_items):
        for item in default_items:
            assert item.company_name == "Apple Inc."

    def test_title_non_empty(self, default_items):
        for item in default_items:
            assert item.title.strip() != ""

    def test_content_non_empty(self, default_items):
        for item in default_items:
            assert item.content.strip() != ""

    def test_source_non_empty(self, default_items):
        for item in default_items:
            assert item.source.strip() != ""

    def test_url_non_empty(self, default_items):
        for item in default_items:
            assert item.url.strip() != ""

    def test_published_at_is_datetime(self, default_items):
        for item in default_items:
            assert isinstance(item.published_at, datetime), (
                f"published_at should be datetime, got {type(item.published_at)}"
            )


# ---------------------------------------------------------------------------
# 11–14. limit parameter
# ---------------------------------------------------------------------------

class TestLimitParameter:
    def test_limit_respected(self, provider):
        items = provider.fetch_news("AAPL", "Apple Inc.", limit=3)
        assert len(items) == 3

    def test_limit_one_returns_single_item(self, provider):
        items = provider.fetch_news("AAPL", "Apple Inc.", limit=1)
        assert len(items) == 1

    def test_limit_zero_returns_empty_list(self, provider):
        items = provider.fetch_news("AAPL", "Apple Inc.", limit=0)
        assert items == []

    def test_limit_larger_than_corpus_returns_all(self, provider):
        """Should return at most len(_MOCK_CORPUS) items."""
        items = provider.fetch_news("AAPL", "Apple Inc.", limit=9999)
        assert len(items) == len(_MOCK_CORPUS)

    def test_default_limit_does_not_exceed_corpus(self, default_items):
        assert len(default_items) <= len(_MOCK_CORPUS)


# ---------------------------------------------------------------------------
# 15. Pydantic round-trip validation
# ---------------------------------------------------------------------------

class TestPydanticRoundTrip:
    def test_items_survive_round_trip(self, default_items):
        """
        Re-construct each returned NewsItem from its own dict representation.
        Confirms that all field values remain valid under the Pydantic contract.
        """
        for item in default_items:
            data = item.model_dump()
            try:
                reconstructed = NewsItem(**data)
            except ValidationError as exc:
                pytest.fail(
                    f"Round-trip validation failed for item {item.news_id}: {exc}"
                )
            assert reconstructed.news_id == item.news_id
            assert reconstructed.symbol  == item.symbol


# ---------------------------------------------------------------------------
# 16. Polymorphic usage
# ---------------------------------------------------------------------------

class TestPolymorphicUsage:
    def test_used_as_base_type(self):
        """Assign to a NewsProvider variable and call through the interface."""
        p: NewsProvider = MockNewsProvider()
        items = p.fetch_news("GOOGL", "Alphabet Inc.", limit=5)
        assert isinstance(items, list)
        assert all(isinstance(i, NewsItem) for i in items)

    def test_abstract_class_cannot_be_instantiated_directly(self):
        with pytest.raises(TypeError):
            NewsProvider()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# 17. Different symbols
# ---------------------------------------------------------------------------

class TestDifferentSymbols:
    def test_symbol_tag_matches_request(self, provider):
        for ticker, company in [
            ("NVDA", "NVIDIA Corporation"),
            ("AMZN", "Amazon.com Inc."),
            ("META", "Meta Platforms Inc."),
        ]:
            items = provider.fetch_news(ticker, company, limit=3)
            assert len(items) == 3
            for item in items:
                assert item.symbol == ticker
                assert item.company_name == company


# ---------------------------------------------------------------------------
# 18. news_id uniqueness
# ---------------------------------------------------------------------------

class TestNewsIdUniqueness:
    def test_news_ids_are_non_empty(self, default_items):
        for item in default_items:
            assert item.news_id.strip() != ""

    def test_news_ids_are_unique_within_result(self, default_items):
        ids = [item.news_id for item in default_items]
        assert len(ids) == len(set(ids)), "Duplicate news_ids found in result set"
