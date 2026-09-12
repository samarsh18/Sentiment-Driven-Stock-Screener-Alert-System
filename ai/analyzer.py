"""
Top-level orchestrator for the AI pipeline. This is the single entry point
other developers (backend routes, background workers, etc.) should call.

Pipeline:
    NewsInput
        -> Stage 1: FinBertSentimentAnalyzer -> SentimentResult
        -> Stage 2: GeminiClient             -> GeminiAnalysis (validated)
        -> decision_engine.evaluate          -> DecisionResult

Failure handling:
    - Stage 1 (FinBERT) failures are recoverable: we fall back to a
      neutral sentiment signal, log a warning, and continue the pipeline
      (a missing/broken open-source model shouldn't take down alerting).
    - Stage 2 (Gemini) failures are NOT silently papered over: we never
      fabricate impact/severity/confidence data, since the decision
      engine's classification depends on it being real. These surface as
      a failed AnalyzerResult with `success=False` and a clear `error`,
      so callers can retry, skip, or surface a degraded state — never
      pretend the analysis is trustworthy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from ai.decision_engine import DecisionThresholds, DEFAULT_THRESHOLDS, evaluate
from ai.finbert import FinBertError, FinBertSentimentAnalyzer
from ai.gemini import GeminiClient, GeminiError
from ai.schemas import (
    DecisionResult,
    GeminiAnalysis,
    NewsInput,
    SentimentResult,
    UserAlertPreferences,
)

logger = logging.getLogger(__name__)

_FALLBACK_SENTIMENT = SentimentResult(sentiment="neutral", sentiment_score=0.0)


@dataclass
class AnalyzerResult:
    """Outcome of running the full pipeline for one news item."""

    news_id: str
    symbol: str
    success: bool
    sentiment_result: Optional[SentimentResult] = None
    gemini_analysis: Optional[GeminiAnalysis] = None
    decision: Optional[DecisionResult] = None
    error: Optional[str] = None
    sentiment_degraded: bool = False  # True if FinBERT failed and we fell back to neutral


def analyze_news(
    news: NewsInput,
    finbert_analyzer: FinBertSentimentAnalyzer,
    gemini_client: GeminiClient,
    user_prefs: Optional[UserAlertPreferences] = None,
    thresholds: DecisionThresholds = DEFAULT_THRESHOLDS,
) -> AnalyzerResult:
    """Runs the full Stage 1 -> Stage 2 -> decision-engine pipeline for a
    single news item.

    Args:
        news: validated news input (see ai.schemas.NewsInput).
        finbert_analyzer: an instance of FinBertSentimentAnalyzer (inject a
            mock `predict_fn` in tests).
        gemini_client: an instance of GeminiClient (inject a mock
            `generate_fn` in tests to avoid real API calls).
        user_prefs: optional per-user minimum-severity preference. Defaults
            to alerting on anything (min_severity=1) if omitted.
        thresholds: decision-engine thresholds; defaults to project spec.
    """
    text_for_sentiment = f"{news.title}\n\n{news.content}"

    sentiment_degraded = False
    try:
        sentiment_result = finbert_analyzer.analyze(text_for_sentiment)
    except FinBertError as exc:
        logger.warning(
            "FinBERT stage failed for news_id=%s; falling back to neutral sentiment: %s",
            news.news_id,
            exc,
        )
        sentiment_result = _FALLBACK_SENTIMENT
        sentiment_degraded = True

    try:
        gemini_analysis = gemini_client.analyze(news, sentiment_result)
    except GeminiError as exc:
        logger.error("Gemini stage failed for news_id=%s: %s", news.news_id, exc)
        return AnalyzerResult(
            news_id=news.news_id,
            symbol=news.symbol,
            success=False,
            sentiment_result=sentiment_result,
            sentiment_degraded=sentiment_degraded,
            error=str(exc),
        )

    decision = evaluate(gemini_analysis, user_prefs=user_prefs, thresholds=thresholds)

    return AnalyzerResult(
        news_id=news.news_id,
        symbol=news.symbol,
        success=True,
        sentiment_result=sentiment_result,
        gemini_analysis=gemini_analysis,
        decision=decision,
        sentiment_degraded=sentiment_degraded,
    )
