"""
backend/app/services/news_relevance.py
---------------------------------------
News Relevance Filter & News Deduplication Service.

Filters raw ingested NewsItem objects using company metadata and deterministic
keyword/symbol relevance scoring. Deduplicates articles by ID, canonical URL,
and title similarity.
"""

from __future__ import annotations

import difflib
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel, Field

from backend.app.models.news import NewsItem

logger = logging.getLogger(__name__)


class StockMetadata(BaseModel):
    """
    Normalized stock and company metadata model.
    """

    symbol: str
    company_name: str
    aliases: List[str] = Field(default_factory=list)
    exchange: Optional[str] = "NSE"
    isin: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap_bucket: Optional[str] = None

    model_config = {
        "extra": "forbid",
        "arbitrary_types_allowed": True,
    }


class RelevanceResult(BaseModel):
    """
    Result of relevance filtering for a single news item.
    """

    relevant: bool
    score: int
    matched_signals: List[str] = Field(default_factory=list)
    reason: str

    model_config = {
        "extra": "forbid",
        "arbitrary_types_allowed": True,
    }


INDIAN_MARKET_KEYWORDS = {
    "nse", "bse", "sebi", "rupees", "inr", "nifty", "sensex", "indian", "india", "dalal street"
}


def _normalize_text(text: str) -> str:
    """Lowercase text and replace whitespace/punctuation sequences with single spaces."""
    if not text:
        return ""
    # Strip punctuation except alphanumeric
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _contains_word_boundary(text: str, word: str) -> bool:
    """Check if a word/symbol appears with word boundaries in text."""
    if not text or not word:
        return False
    pattern = rf"\b{re.escape(word.strip())}\b"
    return bool(re.search(pattern, text, re.IGNORECASE))


def _contains_phrase(text: str, phrase: str) -> bool:
    """Check if a normalized phrase is contained within normalized text."""
    norm_text = _normalize_text(text)
    norm_phrase = _normalize_text(phrase)
    if not norm_text or not norm_phrase:
        return False
    return norm_phrase in norm_text


class NewsRelevanceFilter:
    """
    Evaluates news relevance against target stock metadata using deterministic scoring.
    """

    DEFAULT_THRESHOLD: int = 5

    def __init__(self, threshold: int = 5) -> None:
        self.threshold = threshold

    def evaluate(
        self,
        item: Union[NewsItem, Dict[str, Any], Any],
        metadata: Union[StockMetadata, Dict[str, Any], Any],
        threshold: Optional[int] = None,
    ) -> RelevanceResult:
        """
        Evaluate relevance score and matched signals for a news item.
        """
        thresh = threshold if threshold is not None else self.threshold

        # Extract item fields
        title = str(getattr(item, "title", "") or "")
        content = str(getattr(item, "content", "") or "")

        # Extract metadata fields
        if isinstance(metadata, StockMetadata):
            symbol = metadata.symbol
            company_name = metadata.company_name
            aliases = metadata.aliases or []
            sector = metadata.sector
            industry = metadata.industry
        elif isinstance(metadata, dict):
            symbol = str(metadata.get("symbol", ""))
            company_name = str(metadata.get("company_name", ""))
            aliases = metadata.get("aliases") or []
            sector = metadata.get("sector")
            industry = metadata.get("industry")
        else:
            symbol = str(getattr(metadata, "symbol", "") or "")
            company_name = str(getattr(metadata, "company_name", "") or "")
            aliases = getattr(metadata, "aliases", []) or []
            sector = getattr(metadata, "sector", None)
            industry = getattr(metadata, "industry", None)

        score = 0
        signals: List[str] = []

        # 1. Company Name in Title (+5)
        if company_name and _contains_phrase(title, company_name):
            score += 5
            signals.append("exact_company_name_in_title")

        # 2. Company Name in Content (+3)
        if company_name and _contains_phrase(content, company_name):
            score += 3
            signals.append("exact_company_name_in_content")

        # 3. Symbol in Title (+4)
        if symbol and _contains_word_boundary(title, symbol):
            score += 4
            signals.append("exact_ticker_in_title")

        # 4. Symbol in Content (+2)
        if symbol and _contains_word_boundary(content, symbol):
            score += 2
            signals.append("exact_ticker_in_content")

        # 5. Known Alias in Title (+4)
        alias_title_matched = False
        for alias in aliases:
            if alias and _contains_phrase(title, alias):
                alias_title_matched = True
                break
        if alias_title_matched:
            score += 4
            signals.append("known_alias_in_title")

        # 6. Known Alias in Content (+2)
        alias_content_matched = False
        for alias in aliases:
            if alias and _contains_phrase(content, alias):
                alias_content_matched = True
                break
        if alias_content_matched:
            score += 2
            signals.append("known_alias_in_content")

        # 7. Indian Market / Context Match (+1)
        full_text_norm = _normalize_text(title + " " + content)
        if any(kw in full_text_norm for kw in INDIAN_MARKET_KEYWORDS):
            score += 1
            signals.append("indian_market_context")

        # 8. Sector / Industry Match (+1)
        if sector and _contains_phrase(full_text_norm, sector):
            score += 1
            signals.append("sector_context_match")
        elif industry and _contains_phrase(full_text_norm, industry):
            score += 1
            signals.append("industry_context_match")

        is_relevant = score >= thresh
        reason = (
            f"Score {score} >= threshold {thresh} (signals: {', '.join(signals)})"
            if is_relevant
            else f"Score {score} < threshold {thresh} (signals: {', '.join(signals) or 'none'})"
        )

        return RelevanceResult(
            relevant=is_relevant,
            score=score,
            matched_signals=signals,
            reason=reason,
        )


def evaluate_relevance(
    item: Union[NewsItem, Dict[str, Any], Any],
    metadata: Union[StockMetadata, Dict[str, Any], Any],
    threshold: int = 5,
) -> RelevanceResult:
    """Convenience function to evaluate relevance."""
    filter_svc = NewsRelevanceFilter(threshold=threshold)
    return filter_svc.evaluate(item, metadata)


def filter_relevant_news(
    items: List[Union[NewsItem, Dict[str, Any], Any]],
    metadata: Union[StockMetadata, Dict[str, Any], Any],
    threshold: int = 5,
) -> List[Tuple[Any, RelevanceResult]]:
    """Filter list of news items returning (item, relevance_result) pairs that meet threshold."""
    filter_svc = NewsRelevanceFilter(threshold=threshold)
    results = []
    for item in items or []:
        rel = filter_svc.evaluate(item, metadata)
        if rel.relevant:
            results.append((item, rel))
    return results


# ----------------------------------------------------------------------
# Deduplication Utilities
# ----------------------------------------------------------------------

def _normalize_url(url: str) -> str:
    """Normalize URL by stripping protocol prefix and trailing slashes."""
    if not url:
        return ""
    u = url.strip().lower()
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    return u.rstrip("/")


def _title_similarity(t1: str, t2: str) -> float:
    """
    Calculate deterministic title similarity ratio using Jaccard token set similarity.
    """
    n1 = _normalize_text(t1)
    n2 = _normalize_text(t2)
    if not n1 or not n2:
        return 0.0
    if n1 == n2:
        return 1.0

    w1 = set(n1.split())
    w2 = set(n2.split())
    if not w1 or not w2:
        return 0.0

    jaccard = len(w1 & w2) / float(len(w1 | w2))
    return jaccard


def deduplicate_news(
    items: List[Union[NewsItem, Any]],
    metadata: Optional[Union[StockMetadata, Dict[str, Any], Any]] = None,
    similarity_threshold: float = 0.85,
) -> List[Any]:
    """
    Deduplicate a list of NewsItem objects by news_id, normalized URL,
    and title similarity.

    Preserves the best representative per duplicate cluster based on:
      1. Higher relevance score (if metadata provided)
      2. Earliest published_at timestamp

    Parameters
    ----------
    items : List[Union[NewsItem, Any]]
        List of news items.
    metadata : Optional[StockMetadata]
        Metadata used to calculate relevance scores for representative selection.
    similarity_threshold : float
        Title similarity threshold (default 0.85).

    Returns
    -------
    List[Any]
        Deduplicated list of news items.
    """
    if not items:
        return []

    filter_svc = NewsRelevanceFilter()

    # Pre-calculate scores and publication dates
    item_info = []
    for idx, item in enumerate(items):
        news_id = str(getattr(item, "news_id", "") or "")
        symbol = str(getattr(item, "symbol", "") or "").upper()
        url = _normalize_url(str(getattr(item, "url", "") or ""))
        title = str(getattr(item, "title", "") or "")
        pub_at = getattr(item, "published_at", None)

        if metadata:
            score = filter_svc.evaluate(item, metadata).score
        else:
            score = 0

        item_info.append({
            "index": idx,
            "item": item,
            "news_id": news_id,
            "symbol": symbol,
            "url": url,
            "title": title,
            "pub_at": pub_at,
            "score": score,
        })

    clusters: List[List[Dict[str, Any]]] = []

    for info in item_info:
        matched_cluster = None
        for cluster in clusters:
            for member in cluster:
                # 1. Same news_id
                if info["news_id"] and info["news_id"] == member["news_id"]:
                    matched_cluster = cluster
                    break
                # 2. Same normalized URL
                if info["url"] and info["url"] == member["url"]:
                    matched_cluster = cluster
                    break
                # 3. High title similarity (only if symbols are not different)
                if info["symbol"] and member["symbol"] and info["symbol"] != member["symbol"]:
                    continue
                if _title_similarity(info["title"], member["title"]) >= similarity_threshold:
                    matched_cluster = cluster
                    break
            if matched_cluster:
                break

        if matched_cluster is not None:
            matched_cluster.append(info)
        else:
            clusters.append([info])

    # Select representative for each cluster
    deduped = []
    for cluster in clusters:
        # Sort cluster by score (descending), then pub_at (ascending)
        def _sort_key(x: Dict[str, Any]) -> Tuple[int, datetime]:
            score = x["score"]
            pub = x["pub_at"]
            if isinstance(pub, str):
                try:
                    pub = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                except ValueError:
                    pub = datetime.max.replace(tzinfo=timezone.utc)
            elif pub is None:
                pub = datetime.max.replace(tzinfo=timezone.utc)
            return (-score, pub)

        cluster.sort(key=_sort_key)
        deduped.append(cluster[0]["item"])

    return deduped
