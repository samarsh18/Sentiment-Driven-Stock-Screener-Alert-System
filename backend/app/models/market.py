"""
backend/app/models/market.py
----------------------------
Canonical Pydantic model for normalized historical market OHLCV data.
"""

from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator


class MarketDataBar(BaseModel):
    """Normalized OHLCV bar for a stock symbol."""

    symbol: str
    exchange: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = Field(ge=0.0)

    @field_validator("symbol", "exchange", mode="before")
    @classmethod
    def normalize_str_upper(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("must be a string")
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty or whitespace-only")
        return stripped.upper()

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_utc_datetime(cls, value: object) -> datetime:
        if isinstance(value, str):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        elif isinstance(value, datetime):
            dt = value
        else:
            raise ValueError("timestamp must be a datetime object or ISO-8601 string")

        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    model_config = {
        "extra": "forbid",
        "arbitrary_types_allowed": False,
    }