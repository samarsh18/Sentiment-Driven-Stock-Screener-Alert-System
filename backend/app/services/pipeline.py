"""
backend/app/services/pipeline.py
---------------------------------
End-to-End Processing Pipeline & Orchestration Service.

Connects News Relevance Filtering, Deduplication, AI Analysis, Historical Event
Matching, Event Statistics, Confidence Scoring, and Decision Engine into one
unified, deterministic workflow.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from backend.app.models.news import NewsItem
from backend.app.services.confidence_engine import ConfidenceEngine, ConfidenceResult, calculate_confidence
from backend.app.services.event_statistics import EventStatisticsResult, calculate_event_statistics
from backend.app.services.historical_matcher import (
    HistoricalEventFeatures,
    HistoricalMatchResult,
    match_historical_events,
)
from backend.app.services.news_relevance import (
    NewsRelevanceFilter,
    RelevanceResult,
    StockMetadata,
    deduplicate_news,
    evaluate_relevance,
)

logger = logging.getLogger(__name__)


class PipelineResult(BaseModel):
    """
    Normalized result of the end-to-end stock news processing pipeline.
    """

    news_id: str
    symbol: str
    relevant: bool
    relevance_score: int
    event_type: str = "UNKNOWN"
    sentiment: str = "neutral"
    sentiment_score: float = 0.0
    impact: str = "LOW"
    severity: str = "LOW"
    historical_sample_size: int = 0
    confidence: float = 0.0
    evidence_strength: str = "INSUFFICIENT"
    action: str = "NO_ACTION"
    should_alert: bool = False
    reason: str = ""

    model_config = {
        "extra": "forbid",
        "arbitrary_types_allowed": True,
    }


def default_decision_engine(
    sentiment: str,
    confidence: float,
    evidence_strength: str,
    historical_signal: str,
    severity: str = "LOW",
) -> Tuple[str, bool]:
    """
    Deterministic Decision Engine mapping AI sentiment, confidence, historical signal,
    and severity to actionable decision outputs (action, should_alert).
    """
    clean_sentiment = (sentiment or "neutral").strip().lower()
    clean_severity = (severity or "LOW").strip().upper()

    is_positive = (
        clean_sentiment == "positive"
        or historical_signal in ("STRONG_POSITIVE", "MODERATE_POSITIVE")
    )
    is_negative = (
        clean_sentiment == "negative"
        or historical_signal in ("STRONG_NEGATIVE", "MODERATE_NEGATIVE")
    )

    if is_positive:
        if confidence >= 0.65 or historical_signal == "STRONG_POSITIVE":
            return "BUY", True
        return "ALERT_POSITIVE", True

    if is_negative:
        if (
            confidence >= 0.65
            or historical_signal == "STRONG_NEGATIVE"
            or clean_severity in ("HIGH", "CRITICAL")
        ):
            return "SELL", True
        return "ALERT_NEGATIVE", True

    return "NO_ACTION", False


class StockNewsPipeline:
    """
    Orchestration service connecting relevance filtering, deduplication,
    AI analysis, historical matching, confidence engine, and decision engine.
    """

    def __init__(
        self,
        relevance_threshold: int = 5,
        min_sample_size: int = 30,
        decision_fn: Optional[Callable[..., Tuple[str, bool]]] = None,
    ) -> None:
        self.relevance_threshold = relevance_threshold
        self.min_sample_size = min_sample_size
        self.decision_fn = decision_fn or default_decision_engine
        self.relevance_filter = NewsRelevanceFilter(threshold=relevance_threshold)
        self.confidence_engine = ConfidenceEngine(min_sample_normal=min_sample_size)

    def process_news_item(
        self,
        item: Union[NewsItem, Dict[str, Any], Any],
        metadata: Union[StockMetadata, Dict[str, Any], Any],
        historical_events: Optional[List[Any]] = None,
        ai_analyzer: Optional[Callable[[Any], Dict[str, Any]]] = None,
    ) -> PipelineResult:
        """
        Process a single news item through the complete pipeline.
        """
        news_id = str(getattr(item, "news_id", "") or "")
        symbol = str(getattr(metadata, "symbol", "") or "").upper()

        # Step 1: Relevance Filter
        try:
            rel_res = self.relevance_filter.evaluate(item, metadata, threshold=self.relevance_threshold)
        except Exception as e:
            logger.warning(f"Relevance evaluation failed for news {news_id}: {e}")
            return PipelineResult(
                news_id=news_id,
                symbol=symbol,
                relevant=False,
                relevance_score=0,
                reason=f"Relevance evaluation error: {str(e)}",
            )

        if not rel_res.relevant:
            return PipelineResult(
                news_id=news_id,
                symbol=symbol,
                relevant=False,
                relevance_score=rel_res.score,
                event_type="IRRELEVANT",
                action="NO_ACTION",
                should_alert=False,
                reason=rel_res.reason,
            )

        # Step 2: AI Analysis (FinBERT / Gemini)
        event_type = "GENERAL_NEWS"
        sentiment = "neutral"
        sentiment_score = 0.5
        impact = "LOW"
        severity = "LOW"
        gemini_conf = 0.5

        if ai_analyzer is not None:
            try:
                ai_data = ai_analyzer(item) or {}
                event_type = str(ai_data.get("event_type", event_type))
                sentiment = str(ai_data.get("sentiment", sentiment)).lower()
                sentiment_score = float(ai_data.get("sentiment_score", sentiment_score))
                impact = str(ai_data.get("impact", impact)).upper()
                severity = str(ai_data.get("severity", severity)).upper()
                gemini_conf = float(ai_data.get("gemini_confidence", ai_data.get("confidence", 0.5)))
            except Exception as e:
                logger.warning(f"AI analyzer failed for news {news_id}: {e}")
                return PipelineResult(
                    news_id=news_id,
                    symbol=symbol,
                    relevant=True,
                    relevance_score=rel_res.score,
                    event_type=event_type,
                    sentiment="neutral",
                    confidence=0.20,
                    evidence_strength="INSUFFICIENT",
                    action="NO_ACTION",
                    should_alert=False,
                    reason=f"AI analyzer execution error: {str(e)}",
                )

        # Step 3: Historical Evidence Lookup & Matcher
        matched_events = []
        event_stats = {}
        try:
            target_feat = HistoricalEventFeatures(
                news_id=news_id,
                symbol=symbol,
                event_type=event_type,
                sentiment=sentiment,
                sector=getattr(metadata, "sector", None),
                market_cap_bucket=getattr(metadata, "market_cap_bucket", None),
            )

            if historical_events:
                match_res = match_historical_events(
                    target=target_feat,
                    historical_events=historical_events,
                    min_sample_size=self.min_sample_size,
                )
                matched_events = match_res.matched_events
                event_stats = calculate_event_statistics(matched_events, min_sample_size=self.min_sample_size)
        except Exception as e:
            logger.warning(f"Historical evidence lookup failed for news {news_id}: {e}")

        # Step 4: Confidence Engine
        try:
            conf_res = self.confidence_engine.calculate_confidence(
                event_stats=event_stats,
                gemini_confidence=gemini_conf,
                finbert_score=sentiment_score if sentiment == "positive" else -sentiment_score,
            )
        except Exception as e:
            logger.warning(f"Confidence engine failed for news {news_id}: {e}")
            conf_res = ConfidenceResult(
                confidence=0.20,
                evidence_strength="INSUFFICIENT",
                historical_signal="INSUFFICIENT_DATA",
                reason=f"Confidence calculation error: {str(e)}",
            )

        # Step 5: Decision Engine
        try:
            action, should_alert = self.decision_fn(
                sentiment=sentiment,
                confidence=conf_res.confidence,
                evidence_strength=conf_res.evidence_strength,
                historical_signal=conf_res.historical_signal,
                severity=severity,
            )
        except Exception as e:
            logger.warning(f"Decision engine failed for news {news_id}: {e}")
            action, should_alert = "NO_ACTION", False

        return PipelineResult(
            news_id=news_id,
            symbol=symbol,
            relevant=True,
            relevance_score=rel_res.score,
            event_type=event_type,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            impact=impact,
            severity=severity,
            historical_sample_size=conf_res.sample_size_1d,
            confidence=conf_res.confidence,
            evidence_strength=conf_res.evidence_strength,
            action=action,
            should_alert=should_alert,
            reason=conf_res.reason,
        )

    def process_news_batch(
        self,
        items: List[Union[NewsItem, Dict[str, Any], Any]],
        metadata: Union[StockMetadata, Dict[str, Any], Any],
        historical_events: Optional[List[Any]] = None,
        ai_analyzer: Optional[Callable[[Any], Dict[str, Any]]] = None,
    ) -> List[PipelineResult]:
        """
        Process a batch of news items through relevance filtering, deduplication,
        AI analysis, historical matching, confidence, and decision engine.
        """
        if not items:
            return []

        # Step 1: Relevance Filter
        relevant_items = []
        irrelevant_results = []
        for item in items:
            rel_res = self.relevance_filter.evaluate(item, metadata)
            if rel_res.relevant:
                relevant_items.append(item)
            else:
                news_id = str(getattr(item, "news_id", "") or "")
                symbol = str(getattr(metadata, "symbol", "") or "").upper()
                irrelevant_results.append(
                    PipelineResult(
                        news_id=news_id,
                        symbol=symbol,
                        relevant=False,
                        relevance_score=rel_res.score,
                        event_type="IRRELEVANT",
                        action="NO_ACTION",
                        should_alert=False,
                        reason=rel_res.reason,
                    )
                )

        # Step 2: Deduplication on Relevant Items Only
        deduped_relevant = deduplicate_news(relevant_items, metadata)

        # Step 3: Process Deduped Relevant Items
        pipeline_results = []
        for item in deduped_relevant:
            res = self.process_news_item(
                item=item,
                metadata=metadata,
                historical_events=historical_events,
                ai_analyzer=ai_analyzer,
            )
            pipeline_results.append(res)

        return irrelevant_results + pipeline_results
