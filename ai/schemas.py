"""
Pydantic schemas for the AI pipeline.

These models are the single source of truth for every data contract that
crosses a boundary in the AI subsystem:

    NewsInput        -> what the analyzer receives
    SentimentResult  -> Stage 1 (open-source financial sentiment model) output
    GeminiAnalysis   -> Stage 2 (Gemini) output, validated before use
    UserAlertPreferences -> per-user alerting configuration
    DecisionResult   -> final output of the deterministic decision engine

All AI-produced data (FinBERT normalization, Gemini responses) is validated
against these models before it is trusted anywhere else in the system.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

Sentiment = Literal["positive", "negative", "neutral"]
Impact = Literal["low", "medium", "high"]
Action = Literal["RISK_ALERT", "OPPORTUNITY", "WATCH", "INFORMATIONAL"]


class NewsInput(BaseModel):
    """Contract for a single news item entering the AI pipeline.

    This mirrors the shared "INPUT NEWS CONTRACT" produced upstream by the
    ingestion side of the project (GDELT / market-data ingestion), which is
    NOT owned by this module.
    """

    news_id: str
    symbol: str
    company_name: str
    title: str
    content: str
    source: str
    url: str
    published_at: datetime

    @field_validator("news_id", "symbol", "company_name", "source", "url")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("field must not be blank")
        return value


class SentimentResult(BaseModel):
    """Stage 1 output: normalized result of the open-source sentiment model."""

    sentiment: Sentiment
    sentiment_score: float = Field(ge=-1.0, le=1.0)


class GeminiAnalysis(BaseModel):
    """Stage 2 output: Gemini's structured, validated analysis.

    This is intentionally identical in shape to what we ask Gemini to
    return (see ai/prompts.py) so the raw JSON response can be validated
    directly against this model.
    """

    news_id: str
    symbol: str
    sentiment: Sentiment
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    impact: Impact
    severity: int = Field(ge=1, le=10)
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    summary: str

    @field_validator("reason", "summary")
    @classmethod
    def _not_blank_text(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("field must not be blank")
        return value


class UserAlertPreferences(BaseModel):
    """Per-user alerting preferences consumed by the decision engine.

    Kept intentionally minimal here; the persistence of this model
    (e.g. PostgreSQL storage, API routes to edit it) belongs to other
    developers' ownership areas.
    """

    min_severity: int = Field(default=1, ge=1, le=10)


class DecisionResult(BaseModel):
    """Final, deterministic output of the decision engine."""

    news_id: str
    symbol: str
    action: Action
    should_alert: bool
    severity: int = Field(ge=1, le=10)
    message: str
