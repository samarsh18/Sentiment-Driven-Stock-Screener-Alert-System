"""
tests/test_news_model.py
------------------------
Unit tests for backend.app.models.news.NewsItem.

Coverage:
  1.  Valid NewsItem creation — all fields accepted.
  2.  Missing required field raises ValidationError.
  3.  Empty string raises ValidationError.
  4.  Whitespace-only string raises ValidationError.
  5.  Surrounding whitespace is stripped from string fields.
  6.  Symbol is normalised to uppercase.
  7.  Symbol with surrounding whitespace is stripped then uppercased.
  8.  published_at accepts a datetime object directly.
  9.  published_at accepts a valid ISO-8601 string and coerces it.
  10. published_at rejects a non-datetime garbage string.
  11. Extra fields are forbidden (extra="forbid").
  12. All string fields are independently validated (parametrised).
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.app.models.news import NewsItem

# ---------------------------------------------------------------------------
# Shared fixture — a minimal valid payload
# ---------------------------------------------------------------------------

VALID_PAYLOAD: dict = {
    "news_id": "abc123",
    "symbol": "aapl",
    "company_name": "Apple Inc.",
    "title": "Apple reports record quarterly revenue",
    "content": "Apple Inc. reported record-breaking quarterly revenue today.",
    "source": "Reuters",
    "url": "https://example.com/apple-earnings",
    "published_at": datetime(2024, 1, 15, 9, 30, 0, tzinfo=timezone.utc),
}


def valid(**overrides) -> dict:
    """Return a copy of VALID_PAYLOAD with optional field overrides."""
    return {**VALID_PAYLOAD, **overrides}


# ---------------------------------------------------------------------------
# 1. Valid creation
# ---------------------------------------------------------------------------

class TestValidCreation:
    def test_all_fields_accepted(self):
        item = NewsItem(**VALID_PAYLOAD)
        assert item.news_id == "abc123"
        assert item.symbol == "AAPL"           # normalised to uppercase
        assert item.company_name == "Apple Inc."
        assert item.title == "Apple reports record quarterly revenue"
        assert item.source == "Reuters"
        assert item.url == "https://example.com/apple-earnings"
        assert isinstance(item.published_at, datetime)

    def test_model_fields_are_correct_types(self):
        item = NewsItem(**VALID_PAYLOAD)
        assert isinstance(item.news_id, str)
        assert isinstance(item.symbol, str)
        assert isinstance(item.company_name, str)
        assert isinstance(item.title, str)
        assert isinstance(item.content, str)
        assert isinstance(item.source, str)
        assert isinstance(item.url, str)
        assert isinstance(item.published_at, datetime)


# ---------------------------------------------------------------------------
# 2. Missing required fields
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = [
    "news_id", "symbol", "company_name", "title",
    "content", "source", "url", "published_at",
]

class TestMissingFields:
    @pytest.mark.parametrize("field", REQUIRED_FIELDS)
    def test_missing_field_raises(self, field):
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != field}
        with pytest.raises(ValidationError) as exc_info:
            NewsItem(**payload)
        errors = exc_info.value.errors()
        assert any(e["loc"] == (field,) for e in errors), (
            f"Expected ValidationError on field '{field}', got: {errors}"
        )


# ---------------------------------------------------------------------------
# 3. Empty strings fail
# ---------------------------------------------------------------------------

STRING_FIELDS = [
    "news_id", "symbol", "company_name", "title", "content", "source", "url",
]

class TestEmptyStrings:
    @pytest.mark.parametrize("field", STRING_FIELDS)
    def test_empty_string_raises(self, field):
        with pytest.raises(ValidationError):
            NewsItem(**valid(**{field: ""}))

    @pytest.mark.parametrize("field", STRING_FIELDS)
    def test_whitespace_only_raises(self, field):
        with pytest.raises(ValidationError):
            NewsItem(**valid(**{field: "   "}))

    @pytest.mark.parametrize("field", STRING_FIELDS)
    def test_tab_only_raises(self, field):
        with pytest.raises(ValidationError):
            NewsItem(**valid(**{field: "\t\n"}))


# ---------------------------------------------------------------------------
# 4 & 5. Whitespace stripping
# ---------------------------------------------------------------------------

class TestWhitespaceStripping:
    def test_news_id_stripped(self):
        item = NewsItem(**valid(news_id="  abc123  "))
        assert item.news_id == "abc123"

    def test_company_name_stripped(self):
        item = NewsItem(**valid(company_name="  Apple Inc.  "))
        assert item.company_name == "Apple Inc."

    def test_title_stripped(self):
        item = NewsItem(**valid(title="  Some headline  "))
        assert item.title == "Some headline"

    def test_content_stripped(self):
        item = NewsItem(**valid(content="  Some content.  "))
        assert item.content == "Some content."

    def test_source_stripped(self):
        item = NewsItem(**valid(source="  Reuters  "))
        assert item.source == "Reuters"

    def test_url_stripped(self):
        item = NewsItem(**valid(url="  https://example.com  "))
        assert item.url == "https://example.com"


# ---------------------------------------------------------------------------
# 6 & 7. Symbol normalisation
# ---------------------------------------------------------------------------

class TestSymbolNormalisation:
    def test_lowercase_converted_to_uppercase(self):
        item = NewsItem(**valid(symbol="aapl"))
        assert item.symbol == "AAPL"

    def test_mixed_case_converted_to_uppercase(self):
        item = NewsItem(**valid(symbol="gOoGl"))
        assert item.symbol == "GOOGL"

    def test_already_uppercase_unchanged(self):
        item = NewsItem(**valid(symbol="MSFT"))
        assert item.symbol == "MSFT"

    def test_symbol_whitespace_stripped_then_uppercased(self):
        item = NewsItem(**valid(symbol="  tsla  "))
        assert item.symbol == "TSLA"

    def test_empty_symbol_raises(self):
        with pytest.raises(ValidationError):
            NewsItem(**valid(symbol=""))

    def test_whitespace_only_symbol_raises(self):
        with pytest.raises(ValidationError):
            NewsItem(**valid(symbol="   "))


# ---------------------------------------------------------------------------
# 8 & 9. published_at datetime handling
# ---------------------------------------------------------------------------

class TestPublishedAt:
    def test_accepts_datetime_object(self):
        dt = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        item = NewsItem(**valid(published_at=dt))
        assert item.published_at == dt

    def test_accepts_datetime_without_timezone(self):
        dt = datetime(2024, 6, 1, 12, 0, 0)
        item = NewsItem(**valid(published_at=dt))
        assert item.published_at == dt

    def test_accepts_iso8601_string(self):
        item = NewsItem(**valid(published_at="2024-01-15T09:30:00Z"))
        assert isinstance(item.published_at, datetime)
        assert item.published_at.year == 2024
        assert item.published_at.month == 1
        assert item.published_at.day == 15

    def test_accepts_iso8601_string_with_offset(self):
        item = NewsItem(**valid(published_at="2024-03-20T14:00:00+05:30"))
        assert isinstance(item.published_at, datetime)

    def test_invalid_datetime_string_raises(self):
        with pytest.raises(ValidationError):
            NewsItem(**valid(published_at="not-a-date"))

    def test_numeric_timestamp_raises(self):
        """Raw integers should not be silently coerced to datetime."""
        with pytest.raises(ValidationError):
            NewsItem(**valid(published_at=1234567890))


# ---------------------------------------------------------------------------
# 11. Extra fields are forbidden
# ---------------------------------------------------------------------------

class TestExtraFieldsForbidden:
    def test_extra_field_raises(self):
        with pytest.raises(ValidationError):
            NewsItem(**valid(unexpected_field="should_fail"))
