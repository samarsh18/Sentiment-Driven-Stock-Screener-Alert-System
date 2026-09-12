"""
backend/app/providers/gdelt.py
------------------------------
GDELTNewsProvider — GDELT DOC API v2 news provider implementation.

Queries GDELT for recent news items matching a stock ticker and company name,
normalizes GDELT article data, and produces valid NewsItem Pydantic models.

Resilience:
- User-Agent header included in all HTTP requests.
- Minimum rate-limiting interval between outgoing requests per provider instance.
- Bounded retries with exponential backoff & Retry-After header handling for HTTP 429.
- Graceful exception handling; safely returns [] on exhausted retries without crashing the monitoring worker.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Callable, Optional

import httpx
from pydantic import ValidationError

from backend.app.models.news import NewsItem
from backend.app.providers.base import NewsProvider

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "SentimentDrivenStockScreener/1.0 (Financial News Ingestion Service)"
)


def parse_gdelt_date(date_str: str) -> datetime:
    """
    Parse a GDELT timestamp string into a datetime object with UTC timezone.

    Supported formats:
    - YYYYMMDDHHMMSS (e.g., "20240425133000")
    - YYYYMMDDTHHMMSSZ (e.g., "20240425T133000Z")
    - Standard ISO-8601 strings
    """
    if not isinstance(date_str, str):
        raise ValueError("date_str must be a string")

    clean_str = date_str.strip()
    if not clean_str:
        raise ValueError("empty date string")

    # Format 1: 14-digit compact timestamp "20240425133000"
    if len(clean_str) == 14 and clean_str.isdigit():
        return datetime.strptime(clean_str, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)

    # Format 2: "YYYYMMDDTHHMMSSZ"
    if len(clean_str) == 16 and clean_str.endswith("Z") and "T" in clean_str:
        return datetime.strptime(clean_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)

    # Format 3: Standard ISO-8601
    try:
        dt = datetime.fromisoformat(clean_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except ValueError:
        pass

    raise ValueError(f"Unable to parse GDELT date: {date_str}")


class GDELTNewsProvider(NewsProvider):
    """
    NewsProvider implementation for GDELT DOC API v2 with rate-limiting and retry resilience.
    """

    def __init__(
        self,
        base_url: str = "https://api.gdeltproject.org/api/v2/doc/doc",
        timeout: float = 10.0,
        client: Optional[httpx.Client] = None,
        user_agent: str = DEFAULT_USER_AGENT,
        max_retries: int = 3,
        min_request_interval: float = 5.0,
        sleep_fn: Optional[Callable[[float], None]] = None,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self._client = client
        self.user_agent = user_agent
        self.max_retries = max(1, max_retries)
        self.min_request_interval = max(0.0, min_request_interval)
        self.sleep_fn = sleep_fn or time.sleep
        self._last_request_time: float = 0.0

    def _enforce_rate_limit(self) -> None:
        if self.min_request_interval <= 0.0:
            return
        now = time.monotonic()
        if self._last_request_time > 0:
            elapsed = now - self._last_request_time
            if elapsed < self.min_request_interval:
                wait_time = self.min_request_interval - elapsed
                logger.debug("Rate limiting GDELT request: waiting %.2fs...", wait_time)
                self.sleep_fn(wait_time)
        self._last_request_time = time.monotonic()

    def fetch_news(
        self,
        symbol: str,
        company_name: str,
        limit: int = 20,
    ) -> list[NewsItem]:
        if limit <= 0:
            return []

        clean_symbol = symbol.strip().upper()
        clean_company = company_name.strip()

        query_str = f'"{clean_company}" OR "{clean_symbol}"'
        max_records = min(limit, 250)

        params = {
            "query": query_str,
            "mode": "artlist",
            "maxrecords": str(max_records),
            "format": "json",
        }

        headers = {
            "User-Agent": self.user_agent,
        }

        data: Optional[dict] = None

        for attempt in range(1, self.max_retries + 1):
            self._enforce_rate_limit()

            try:
                if self._client is not None:
                    response = self._client.get(
                        self.base_url,
                        params=params,
                        headers=headers,
                        timeout=self.timeout,
                    )
                else:
                    with httpx.Client(timeout=self.timeout) as client:
                        response = client.get(
                            self.base_url,
                            params=params,
                            headers=headers,
                        )

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    backoff = 5.0 * attempt
                    if retry_after:
                        try:
                            parsed_retry = float(retry_after.strip())
                            if 0 < parsed_retry <= 30:
                                backoff = parsed_retry
                        except ValueError:
                            pass

                    logger.warning(
                        "GDELT API HTTP 429 Rate Limited for symbol=%s (attempt %d/%d). Waiting %.1fs...",
                        clean_symbol,
                        attempt,
                        self.max_retries,
                        backoff,
                    )
                    if attempt < self.max_retries:
                        self.sleep_fn(backoff)
                        continue
                    else:
                        logger.warning(
                            "GDELT API retries exhausted for symbol=%s; safely returning empty list.",
                            clean_symbol,
                        )
                        return []

                response.raise_for_status()
                data = response.json()
                logger.info(
                    "GDELT API request succeeded for symbol=%s (HTTP %d, attempt %d)",
                    clean_symbol,
                    response.status_code,
                    attempt,
                )
                break

            except (httpx.HTTPError, httpx.RequestError, httpx.TimeoutException, json.JSONDecodeError, Exception) as exc:
                backoff = 2.0 * attempt
                logger.warning(
                    "GDELT API request failed for symbol=%s (attempt %d/%d): %s",
                    clean_symbol,
                    attempt,
                    self.max_retries,
                    exc,
                )
                if attempt < self.max_retries:
                    self.sleep_fn(backoff)
                else:
                    logger.warning(
                        "GDELT API max retries (%d) reached for symbol=%s; returning empty list.",
                        self.max_retries,
                        clean_symbol,
                    )
                    return []

        if not isinstance(data, dict):
            return []

        articles = data.get("articles")
        if not isinstance(articles, list):
            return []

        items: list[NewsItem] = []
        for article in articles:
            if not isinstance(article, dict):
                continue
            item = self._parse_article(article, clean_symbol, clean_company)
            if item is not None:
                items.append(item)
                if len(items) >= limit:
                    break

        return items

    def _parse_article(
        self,
        article: dict,
        symbol: str,
        company_name: str,
    ) -> Optional[NewsItem]:
        url = article.get("url")
        if not isinstance(url, str) or not url.strip():
            return None
        url = url.strip()

        url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        news_id = f"GDELT-{url_hash}"

        title = article.get("title")
        if not isinstance(title, str) or not title.strip():
            return None
        title = title.strip()

        content = article.get("snippet") or article.get("content") or title
        if not isinstance(content, str) or not content.strip():
            content = title
        else:
            content = content.strip()

        source = article.get("domain") or article.get("source") or "GDELT"
        if not isinstance(source, str) or not source.strip():
            source = "GDELT"
        else:
            source = source.strip()

        raw_date = article.get("seendate")
        if not raw_date:
            return None

        try:
            published_at = parse_gdelt_date(str(raw_date))
        except ValueError:
            return None

        try:
            return NewsItem(
                news_id=news_id,
                symbol=symbol,
                company_name=company_name,
                title=title,
                content=content,
                source=source,
                url=url,
                published_at=published_at,
            )
        except ValidationError:
            return None