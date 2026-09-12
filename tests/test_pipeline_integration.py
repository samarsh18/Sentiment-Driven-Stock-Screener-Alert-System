"""
tests/test_pipeline_integration.py
-----------------------------------
End-to-End Pipeline Integration Tests.

Verifies end-to-end processing across Relevance Filtering, Deduplication,
AI Analysis, Historical Event Matching, Event Statistics, Confidence Engine,
and Decision Engine.

All tests are 100% offline, deterministic, and mock external network dependencies.
"""

from datetime import datetime, timezone
import pytest

from backend.app.models.news import NewsItem
from backend.app.services.event_study import EventStudyResult
from backend.app.services.historical_matcher import HistoricalEventFeatures
from backend.app.services.news_relevance import StockMetadata
from backend.app.services.pipeline import PipelineResult, StockNewsPipeline


def make_news(
    news_id: str,
    symbol: str = "TATAMOTORS",
    title: str = "Tata Motors wins major EV contract",
    content: str = "Tata Consultancy Services and Tata Motors announced major contract win.",
    url: str = "https://example.com/news/1",
) -> NewsItem:
    return NewsItem(
        news_id=news_id,
        symbol=symbol,
        company_name="Tata Motors",
        title=title,
        content=content,
        source="GDELT",
        url=url,
        published_at=datetime(2024, 4, 1, 12, 0, 0, tzinfo=timezone.utc),
    )


def make_meta(
    symbol: str = "TATAMOTORS",
    company_name: str = "Tata Motors",
    sector: str = "AUTOMOBILE",
) -> StockMetadata:
    return StockMetadata(
        symbol=symbol,
        company_name=company_name,
        aliases=["Tata Motors Ltd"],
        sector=sector,
        market_cap_bucket="LARGE",
    )


def make_historical_pool(
    event_type: str = "MAJOR_CONTRACT",
    count: int = 40,
    r1d: float = 0.05,
) -> list[HistoricalEventFeatures]:
    events = []
    for i in range(count):
        es = EventStudyResult(
            news_id=f"HIST-{i}",
            symbol="MARUTI" if i % 2 == 0 else "M&M",
            exchange="NSE",
            event_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            excess_return_1d=r1d,
            excess_return_3d=r1d + 0.02,
            excess_return_5d=r1d + 0.04,
        )
        events.append(
            HistoricalEventFeatures(
                news_id=f"HIST-{i}",
                symbol="MARUTI" if i % 2 == 0 else "M&M",
                event_type=event_type,
                sentiment="positive" if r1d > 0 else "negative",
                sector="AUTOMOBILE",
                market_cap_bucket="LARGE",
                event_study=es,
            )
        )
    return events


class TestPipelineIntegration:
    def test_positive_event_pipeline(self):
        pipeline = StockNewsPipeline()
        meta = make_meta()
        item = make_news(
            news_id="N-POS",
            title="Tata Motors wins major EV manufacturing contract",
            content="Tata Motors signed a major multi-billion contract for EV trucks.",
        )
        history = make_historical_pool(event_type="MAJOR_CONTRACT", count=40, r1d=0.05)

        def mock_ai_analyzer(article):
            return {
                "event_type": "MAJOR_CONTRACT",
                "sentiment": "positive",
                "sentiment_score": 0.90,
                "impact": "HIGH",
                "severity": "LOW",
                "gemini_confidence": 0.85,
            }

        res = pipeline.process_news_item(
            item=item,
            metadata=meta,
            historical_events=history,
            ai_analyzer=mock_ai_analyzer,
        )

        assert res.relevant is True
        assert res.relevance_score >= 5
        assert res.event_type == "MAJOR_CONTRACT"
        assert res.sentiment == "positive"
        assert res.historical_sample_size == 40
        assert res.confidence > 0.60
        assert res.evidence_strength in ("STRONG", "MODERATE")
        assert res.action in ("BUY", "ALERT_POSITIVE")
        assert res.should_alert is True
        assert len(res.reason) > 0

    def test_negative_event_pipeline(self):
        pipeline = StockNewsPipeline()
        meta = make_meta()
        item = make_news(
            news_id="N-NEG",
            title="Tata Motors faces major product recall",
            content="Tata Motors issued a safety recall for 50,000 vehicles in India.",
            url="https://example.com/recall",
        )
        history = make_historical_pool(event_type="PRODUCT_RECALL", count=35, r1d=-0.06)

        def mock_ai_analyzer(article):
            return {
                "event_type": "PRODUCT_RECALL",
                "sentiment": "negative",
                "sentiment_score": 0.88,
                "impact": "HIGH",
                "severity": "HIGH",
                "gemini_confidence": 0.90,
            }

        res = pipeline.process_news_item(
            item=item,
            metadata=meta,
            historical_events=history,
            ai_analyzer=mock_ai_analyzer,
        )

        assert res.relevant is True
        assert res.sentiment == "negative"
        assert res.severity == "HIGH"
        assert res.confidence > 0.60
        assert res.action in ("SELL", "ALERT_NEGATIVE")
        assert res.should_alert is True

    def test_irrelevant_article_pipeline(self):
        pipeline = StockNewsPipeline()
        meta = make_meta()
        item = make_news(
            news_id="N-IRRELEVANT",
            title="Weather forecast for Chennai",
            content="Heavy rainfall is expected in coastal areas of Tamil Nadu tomorrow.",
            url="https://example.com/weather",
        )

        ai_called = False

        def mock_ai_analyzer(article):
            nonlocal ai_called
            ai_called = True
            return {"event_type": "WEATHER"}

        res = pipeline.process_news_item(
            item=item,
            metadata=meta,
            ai_analyzer=mock_ai_analyzer,
        )

        assert res.relevant is False
        assert ai_called is False
        assert res.action == "NO_ACTION"
        assert res.should_alert is False

    def test_duplicate_article_batch(self):
        pipeline = StockNewsPipeline()
        meta = make_meta()
        item1 = make_news(news_id="DUP-1", title="Tata Motors Q4 profit jumps 50%", url="https://ex.com/tata1")
        item2 = make_news(news_id="DUP-2", title="Tata Motors Q4 profit jumps 50%!", url="https://ex.com/tata2")

        ai_call_count = 0

        def mock_ai_analyzer(article):
            nonlocal ai_call_count
            ai_call_count += 1
            return {
                "event_type": "EARNINGS_RELEASE",
                "sentiment": "positive",
                "sentiment_score": 0.85,
            }

        results = pipeline.process_news_batch(
            items=[item1, item2],
            metadata=meta,
            ai_analyzer=mock_ai_analyzer,
        )

        # 2 items passed in, 1 duplicate collapsed -> only 1 processed by AI pipeline
        assert ai_call_count == 1
        relevant_processed = [r for r in results if r.relevant]
        assert len(relevant_processed) == 1

    def test_insufficient_historical_evidence_pipeline(self):
        pipeline = StockNewsPipeline()
        meta = make_meta()
        item = make_news(
            news_id="N-SPARSE",
            title="Tata Motors announces minor battery technology study",
            content="Tata Motors partnered with a university lab for battery research.",
        )
        # Small historical pool N=5 (< 10)
        history = make_historical_pool(event_type="RESEARCH", count=5, r1d=0.02)

        def mock_ai_analyzer(article):
            return {
                "event_type": "RESEARCH",
                "sentiment": "positive",
                "sentiment_score": 0.70,
                "gemini_confidence": 0.95,  # High LLM confidence
            }

        res = pipeline.process_news_item(
            item=item,
            metadata=meta,
            historical_events=history,
            ai_analyzer=mock_ai_analyzer,
        )

        assert res.relevant is True
        # Confidence is capped at <= 0.35 because N < 10
        assert res.confidence <= 0.35
        assert res.evidence_strength == "INSUFFICIENT"

    def test_pipeline_failure_handling(self):
        pipeline = StockNewsPipeline()
        meta = make_meta()
        item = make_news(
            news_id="N-FAIL",
            title="Tata Motors quarterly update",
            content="Tata Motors published financial report.",
        )

        def failing_ai_analyzer(article):
            raise RuntimeError("Downstream AI model API timeout error")

        # Must return controlled result without raising an uncaught exception
        res = pipeline.process_news_item(
            item=item,
            metadata=meta,
            ai_analyzer=failing_ai_analyzer,
        )

        assert isinstance(res, PipelineResult)
        assert res.relevant is True
        assert res.confidence == 0.20
        assert res.evidence_strength == "INSUFFICIENT"
        assert res.action == "NO_ACTION"
        assert res.should_alert is False
        assert "AI analyzer execution error" in res.reason
