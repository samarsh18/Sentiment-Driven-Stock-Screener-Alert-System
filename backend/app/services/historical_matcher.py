"""
backend/app/services/historical_matcher.py
--------------------------------------------
Historical Event Matcher Service.

Compares target event features against historical events using progressive
fallback matching across 4 priority tiers:
  Tier 1: event_type + sentiment + sector + market_cap_bucket
  Tier 2: event_type + sentiment + sector
  Tier 3: event_type + sentiment
  Tier 4: event_type
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from backend.app.services.event_study import EventStudyResult

logger = logging.getLogger(__name__)


class HistoricalEventFeatures(BaseModel):
    """
    Normalized feature representation of a financial news event for matching.
    """

    news_id: str
    symbol: str
    event_type: Optional[str] = None
    sentiment: Optional[str] = None
    sector: Optional[str] = None
    market_cap_bucket: Optional[str] = None
    event_date: Optional[Union[datetime, date, str]] = None
    event_study: Optional[EventStudyResult] = None

    model_config = {
        "extra": "forbid",
        "arbitrary_types_allowed": True,
    }


class HistoricalMatchResult(BaseModel):
    """
    Result returned by the Historical Event Matcher.
    """

    matched_events: List[HistoricalEventFeatures] = Field(default_factory=list)
    match_tier: int = 0
    match_reason: str = ""
    sample_size: int = 0
    sufficient_sample: bool = False

    model_config = {
        "extra": "forbid",
        "arbitrary_types_allowed": True,
    }


def _norm_str(val: Any) -> Optional[str]:
    """Normalize a string field by stripping whitespace and converting to uppercase."""
    if val is None:
        return None
    s = str(val).strip()
    return s.upper() if s else None


def _extract_features(item: Any) -> HistoricalEventFeatures:
    """Coerce various input types into a HistoricalEventFeatures model."""
    if isinstance(item, HistoricalEventFeatures):
        return item
    if isinstance(item, dict):
        return HistoricalEventFeatures(
            news_id=str(item.get("news_id", "")),
            symbol=str(item.get("symbol", "")),
            event_type=item.get("event_type"),
            sentiment=item.get("sentiment"),
            sector=item.get("sector"),
            market_cap_bucket=item.get("market_cap_bucket"),
            event_date=item.get("event_date") or item.get("published_at"),
            event_study=item.get("event_study"),
        )
    return HistoricalEventFeatures(
        news_id=str(getattr(item, "news_id", "")),
        symbol=str(getattr(item, "symbol", "")),
        event_type=getattr(item, "event_type", None),
        sentiment=getattr(item, "sentiment", None),
        sector=getattr(item, "sector", None),
        market_cap_bucket=getattr(item, "market_cap_bucket", None),
        event_date=getattr(item, "event_date", getattr(item, "published_at", None)),
        event_study=getattr(item, "event_study", None),
    )


class HistoricalEventMatcher:
    """
    Matches target news events against a repository of historical news events
    using progressive fallback matching strategy across 4 priority tiers.
    """

    def __init__(self, min_sample_size: int = 30, max_sample_size: int = 500) -> None:
        self.min_sample_size = max(1, min_sample_size)
        self.max_sample_size = max(1, max_sample_size)

    def match(
        self,
        target: Union[HistoricalEventFeatures, Dict[str, Any], Any],
        historical_events: List[Union[HistoricalEventFeatures, Dict[str, Any], Any]],
        min_sample_size: Optional[int] = None,
        max_sample_size: Optional[int] = None,
    ) -> HistoricalMatchResult:
        """
        Execute progressive fallback matching.

        Parameters
        ----------
        target : HistoricalEventFeatures | dict | Any
            Target event to match.
        historical_events : List[HistoricalEventFeatures | dict | Any]
            Pool of historical events.
        min_sample_size : Optional[int]
            Override default MIN_SAMPLE_SIZE for this run.
        max_sample_size : Optional[int]
            Override default MAX_SAMPLE_SIZE for this run.

        Returns
        -------
        HistoricalMatchResult
        """
        min_size = min_sample_size if min_sample_size is not None else self.min_sample_size
        max_size = max_sample_size if max_sample_size is not None else self.max_sample_size

        target_feat = _extract_features(target)
        target_event_type = _norm_str(target_feat.event_type)
        target_sentiment = _norm_str(target_feat.sentiment)
        target_sector = _norm_str(target_feat.sector)
        target_mcap = _norm_str(target_feat.market_cap_bucket)

        if not target_event_type:
            return HistoricalMatchResult(
                matched_events=[],
                match_tier=0,
                match_reason="Target event_type is missing or empty",
                sample_size=0,
                sufficient_sample=False,
            )

        # Deduplicate historical events by news_id
        seen_news_ids = set()
        deduped_history: List[HistoricalEventFeatures] = []
        for raw_item in historical_events or []:
            feat = _extract_features(raw_item)
            if feat.news_id and feat.news_id not in seen_news_ids:
                seen_news_ids.add(feat.news_id)
                deduped_history.append(feat)

        # Base candidate pool matching event_type (Tier 4)
        tier_4_matches = [
            item for item in deduped_history
            if _norm_str(item.event_type) == target_event_type
        ]

        if not tier_4_matches:
            return HistoricalMatchResult(
                matched_events=[],
                match_tier=0,
                match_reason="No historical events found matching event_type",
                sample_size=0,
                sufficient_sample=False,
            )

        # Tier 3 matches: Tier 4 + same sentiment
        tier_3_matches = [
            item for item in tier_4_matches
            if _norm_str(item.sentiment) == target_sentiment
        ]

        # Tier 2 matches: Tier 3 + same sector
        tier_2_matches = [
            item for item in tier_3_matches
            if _norm_str(item.sector) == target_sector
        ]

        # Tier 1 matches: Tier 2 + same market_cap_bucket
        tier_1_matches = [
            item for item in tier_2_matches
            if _norm_str(item.market_cap_bucket) == target_mcap
        ]

        # Progressive Fallback Evaluation: Tier 1 -> Tier 2 -> Tier 3 -> Tier 4
        if len(tier_1_matches) >= min_size:
            matched = tier_1_matches[:max_size]
            return HistoricalMatchResult(
                matched_events=matched,
                match_tier=1,
                match_reason="Matched event_type, sentiment, sector, and market_cap_bucket (Tier 1)",
                sample_size=len(matched),
                sufficient_sample=True,
            )

        if len(tier_2_matches) >= min_size:
            matched = tier_2_matches[:max_size]
            return HistoricalMatchResult(
                matched_events=matched,
                match_tier=2,
                match_reason="Matched event_type, sentiment, and sector (Tier 2)",
                sample_size=len(matched),
                sufficient_sample=True,
            )

        if len(tier_3_matches) >= min_size:
            matched = tier_3_matches[:max_size]
            return HistoricalMatchResult(
                matched_events=matched,
                match_tier=3,
                match_reason="Matched event_type and sentiment (Tier 3)",
                sample_size=len(matched),
                sufficient_sample=True,
            )

        if len(tier_4_matches) >= min_size:
            matched = tier_4_matches[:max_size]
            return HistoricalMatchResult(
                matched_events=matched,
                match_tier=4,
                match_reason="Matched event_type (Tier 4)",
                sample_size=len(matched),
                sufficient_sample=True,
            )

        # Insufficient sample fallback: return Tier 4 matches with sufficient_sample=False
        matched = tier_4_matches[:max_size]
        return HistoricalMatchResult(
            matched_events=matched,
            match_tier=4,
            match_reason=f"Insufficient sample size ({len(tier_4_matches)} < {min_size}); fallback to Tier 4 matches",
            sample_size=len(matched),
            sufficient_sample=False,
        )


def match_historical_events(
    target: Union[HistoricalEventFeatures, Dict[str, Any], Any],
    historical_events: List[Union[HistoricalEventFeatures, Dict[str, Any], Any]],
    min_sample_size: int = 30,
    max_sample_size: int = 500,
) -> HistoricalMatchResult:
    """
    Convenience function to match target events against historical events.
    """
    matcher = HistoricalEventMatcher(min_sample_size=min_sample_size, max_sample_size=max_sample_size)
    return matcher.match(target, historical_events)
