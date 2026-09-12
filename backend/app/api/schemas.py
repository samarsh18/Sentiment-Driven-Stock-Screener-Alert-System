"""
backend/app/api/schemas.py
---------------------------
Pydantic v2 request / response schemas for the REST API.

These are intentionally separate from the internal service models so that
the public API contract can evolve independently of the internal domain.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

SEVERITY_LABEL_MAP: dict[int, str] = {
    1: "LOW", 2: "LOW", 3: "LOW",
    4: "MEDIUM", 5: "MEDIUM", 6: "MEDIUM",
    7: "HIGH", 8: "HIGH", 9: "HIGH", 10: "HIGH",
}
SEVERITY_INT_MAP: dict[str, int] = {
    "LOW": 3, "MEDIUM": 5, "HIGH": 8, "CRITICAL": 10,
}


def severity_to_label(severity_int: int) -> str:
    """Map integer severity (1–10) to string label."""
    return SEVERITY_LABEL_MAP.get(max(1, min(10, severity_int)), "LOW")


def severity_label_to_int(label: str) -> int:
    """Map string severity label to representative integer."""
    return SEVERITY_INT_MAP.get(label.upper(), 3)


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    email: str = Field(..., description="User email address")

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.strip().lower()


class UserResponse(BaseModel):
    id: int
    email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Watchlist schemas
# ---------------------------------------------------------------------------

class WatchlistItemCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    company_name: str = Field(..., min_length=1, max_length=255)

    @field_validator("symbol")
    @classmethod
    def normalise_symbol(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("company_name")
    @classmethod
    def strip_company(cls, v: str) -> str:
        return v.strip()


class WatchlistItemResponse(BaseModel):
    id: int
    user_id: int
    symbol: str
    company_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class WatchlistResponse(BaseModel):
    items: List[WatchlistItemResponse]
    total: int


# ---------------------------------------------------------------------------
# News schemas
# ---------------------------------------------------------------------------

class NewsRecordResponse(BaseModel):
    id: int
    news_id: str
    symbol: str
    company_name: str
    title: str
    content: str
    source: str
    url: str
    published_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class NewsListResponse(BaseModel):
    items: List[NewsRecordResponse]
    pagination: PaginationMeta


# ---------------------------------------------------------------------------
# Alert schemas
# ---------------------------------------------------------------------------

class AlertResponse(BaseModel):
    id: int
    alert_id: str
    user_id: Optional[int]
    symbol: str
    action: str
    severity: int
    severity_label: str
    message: str
    should_alert: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_record(cls, record: object) -> "AlertResponse":
        return cls(
            id=record.id,
            alert_id=record.alert_id,
            user_id=record.user_id,
            symbol=record.symbol,
            action=record.action,
            severity=record.severity,
            severity_label=severity_to_label(record.severity),
            message=record.message,
            should_alert=record.should_alert,
            created_at=record.created_at,
        )


class AlertListResponse(BaseModel):
    items: List[AlertResponse]
    pagination: PaginationMeta


# ---------------------------------------------------------------------------
# Market / Prices schemas
# ---------------------------------------------------------------------------

class PriceBarResponse(BaseModel):
    symbol: str
    exchange: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class PricesListResponse(BaseModel):
    symbol: str
    exchange: str
    items: List[PriceBarResponse]
    total: int


# ---------------------------------------------------------------------------
# Pipeline / Analyze schemas
# ---------------------------------------------------------------------------

class StockMetadataInput(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    company_name: str = Field(..., min_length=1, max_length=255)
    aliases: List[str] = Field(default_factory=list)
    exchange: str = "NSE"
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap_bucket: Optional[str] = None

    @field_validator("symbol")
    @classmethod
    def normalise_symbol(cls, v: str) -> str:
        return v.strip().upper()


class NewsItemInput(BaseModel):
    news_id: str
    symbol: str
    company_name: str
    title: str
    content: str
    source: str
    url: str
    published_at: datetime


class PipelineAnalyzeRequest(BaseModel):
    news_item: NewsItemInput
    stock_metadata: StockMetadataInput
    ai_sentiment: Optional[str] = None          # "positive" / "negative" / "neutral"
    ai_sentiment_score: Optional[float] = None  # 0.0 – 1.0
    ai_event_type: Optional[str] = None
    ai_impact: Optional[str] = None
    ai_severity: Optional[str] = None           # "LOW" / "MEDIUM" / "HIGH" / "CRITICAL"
    gemini_confidence: Optional[float] = None
    persist_alert: bool = False
    user_id: Optional[int] = None


class PipelineAnalyzeResponse(BaseModel):
    news_id: str
    symbol: str
    relevant: bool
    relevance_score: int
    event_type: str
    sentiment: str
    sentiment_score: float
    impact: str
    severity_label: str
    confidence: float
    evidence_strength: str
    action: str
    should_alert: bool
    reason: str
    alert_id: Optional[str] = None


# ---------------------------------------------------------------------------
# User Preferences schemas  (simple key-value store on top of existing model)
# ---------------------------------------------------------------------------

class UserPreferencesResponse(BaseModel):
    user_id: int
    is_active: bool
    email: str

    @classmethod
    def from_user(cls, user) -> "UserPreferencesResponse":
        return cls(user_id=user.id, is_active=user.is_active, email=user.email)


class UserPreferencesUpdate(BaseModel):
    is_active: Optional[bool] = None
