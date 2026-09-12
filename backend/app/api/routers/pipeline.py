"""
backend/app/api/routers/pipeline.py
--------------------------------------
Pipeline / Analyze endpoint.

POST /api/pipeline/analyze

Accepts a news item + stock metadata + optional AI analysis outputs,
runs through the StockNewsPipeline deterministically, and returns a
structured result. Optionally persists an AlertRecord.
"""
from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.api.schemas import (
    PipelineAnalyzeRequest,
    PipelineAnalyzeResponse,
    severity_label_to_int,
)
from backend.app.database.repository import create_alert
from backend.app.database.seed_historical_events import get_seeded_historical_events
from backend.app.models.news import NewsItem
from backend.app.services.news_relevance import StockMetadata
from backend.app.services.pipeline import StockNewsPipeline

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline"])

_pipeline = StockNewsPipeline()


@router.post(
    "/analyze",
    response_model=PipelineAnalyzeResponse,
    status_code=status.HTTP_200_OK,
)
def analyze_news(body: PipelineAnalyzeRequest, db: Session = Depends(get_db)):
    """
    Run a news article through the processing pipeline.

    The caller may supply pre-computed AI analysis (sentiment, event_type, etc.)
    via optional fields. These are injected into the pipeline as a mock AI analyzer
    so that the API remains fully offline and deterministic.

    When USE_SEED_HISTORICAL_EVENTS is enabled (default: true), a deterministic
    seed pool of historical event observations is supplied to the historical matcher,
    enabling full statistical event-study evaluation during live demonstrations.

    If persist_alert=True and should_alert=True in the result, an AlertRecord
    is written to the database.
    """
    news_item = NewsItem(
        news_id=body.news_item.news_id,
        symbol=body.news_item.symbol,
        company_name=body.news_item.company_name,
        title=body.news_item.title,
        content=body.news_item.content,
        source=body.news_item.source,
        url=body.news_item.url,
        published_at=body.news_item.published_at,
    )

    metadata = StockMetadata(
        symbol=body.stock_metadata.symbol,
        company_name=body.stock_metadata.company_name,
        aliases=body.stock_metadata.aliases,
        exchange=body.stock_metadata.exchange,
        sector=body.stock_metadata.sector,
        industry=body.stock_metadata.industry,
        market_cap_bucket=body.stock_metadata.market_cap_bucket,
    )

    # Build a lightweight AI analyzer from the provided pre-computed values
    ai_data = {
        "event_type": body.ai_event_type or "GENERAL_NEWS",
        "sentiment": body.ai_sentiment or "neutral",
        "sentiment_score": body.ai_sentiment_score or 0.5,
        "impact": body.ai_impact or "LOW",
        "severity": body.ai_severity or "LOW",
        "gemini_confidence": body.gemini_confidence or 0.5,
    }

    def _precomputed_analyzer(_item):
        return ai_data

    # Load seed pool of historical event observations if seed mode is active
    historical_events = None
    use_seed_raw = os.getenv("USE_SEED_HISTORICAL_EVENTS", "true").strip().lower()
    if use_seed_raw not in ("false", "0", "no", "off"):
        historical_events = get_seeded_historical_events()

    result = _pipeline.process_news_item(
        item=news_item,
        metadata=metadata,
        historical_events=historical_events,
        ai_analyzer=_precomputed_analyzer,
    )

    alert_id = None
    if body.persist_alert and result.should_alert:
        alert_id = str(uuid.uuid4())
        severity_int = severity_label_to_int(result.severity)
        create_alert(
            db=db,
            alert_id=alert_id,
            symbol=result.symbol,
            action=result.action,
            severity=severity_int,
            message=result.reason[:2000],
            user_id=body.user_id,
            should_alert=True,
        )

    return PipelineAnalyzeResponse(
        news_id=result.news_id,
        symbol=result.symbol,
        relevant=result.relevant,
        relevance_score=result.relevance_score,
        event_type=result.event_type,
        sentiment=result.sentiment,
        sentiment_score=result.sentiment_score,
        impact=result.impact,
        severity_label=result.severity,
        historical_sample_size=result.historical_sample_size,
        confidence=result.confidence,
        evidence_strength=result.evidence_strength,
        action=result.action,
        should_alert=result.should_alert,
        reason=result.reason,
        alert_id=alert_id,
    )
