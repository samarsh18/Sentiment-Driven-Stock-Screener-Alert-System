"""
backend/app/models/news.py
--------------------------
Canonical data contract for a normalized financial news item.

This is a pure Pydantic model — it has no database, API, or AI coupling.
Person 1 (data-monitoring) produces NewsItem objects after ingestion.
Person 3 (hybrid-ai) consumes them for sentiment analysis.
Person 2 (backend-database) persists them via its own ORM layer.

Normalized News Contract
------------------------
{
    "news_id":      str   — unique identifier (e.g. content hash or provider ID)
    "symbol":       str   — stock ticker, always uppercase  (e.g. "AAPL")
    "company_name": str   — human-readable company name
    "title":        str   — article headline
    "content":      str   — article body or summary
    "source":       str   — provider name (e.g. "GDELT", "Reuters")
    "url":          str   — original article URL
    "published_at": datetime — UTC publication timestamp (ISO-8601)
}
"""

from datetime import datetime

from pydantic import BaseModel, field_validator


class NewsItem(BaseModel):
    """Normalized financial news item produced by the ingestion pipeline."""

    news_id: str
    symbol: str
    company_name: str
    title: str
    content: str
    source: str
    url: str
    published_at: datetime

    # ------------------------------------------------------------------
    # Field-level validators
    # ------------------------------------------------------------------

    @field_validator(
        "news_id", "company_name", "title", "content", "source", "url",
        mode="before",
    )
    @classmethod
    def strip_and_require(cls, value: object) -> str:
        """Strip surrounding whitespace and reject empty strings."""
        if not isinstance(value, str):
            raise ValueError("must be a string")
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty or whitespace-only")
        return stripped

    @field_validator("symbol", mode="before")
    @classmethod
    def normalise_symbol(cls, value: object) -> str:
        """Strip whitespace and convert ticker symbol to uppercase."""
        if not isinstance(value, str):
            raise ValueError("must be a string")
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty or whitespace-only")
        return stripped.upper()

    @field_validator("published_at", mode="before")
    @classmethod
    def require_datetime_or_string(cls, value: object) -> object:
        """
        Accept only datetime objects or strings.

        Pydantic v2 silently coerces integers (Unix timestamps) to datetime.
        This validator rejects that coercion — callers must always supply an
        explicit datetime or a parseable ISO-8601 string.
        """
        if isinstance(value, (datetime, str)):
            return value
        raise ValueError(
            f"published_at must be a datetime object or ISO-8601 string, "
            f"got {type(value).__name__}"
        )

    # ------------------------------------------------------------------
    # Model configuration
    # ------------------------------------------------------------------

    model_config = {
        # Forbid extra fields so callers cannot accidentally pass unknown keys.
        "extra": "forbid",
        # Allow datetime objects to be passed directly (not just strings).
        "arbitrary_types_allowed": False,
    }
