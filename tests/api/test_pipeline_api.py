"""
tests/api/test_pipeline_api.py
--------------------------------
Tests for the Pipeline Analyze API endpoint.

POST /api/pipeline/analyze

All tests are deterministic and offline — no Gemini calls, no network.
"""
from datetime import datetime, timezone

BASE_NEWS = {
    "news_id": "PIPE-TEST-001",
    "symbol": "TCS",
    "company_name": "Tata Consultancy Services",
    "title": "TCS beats quarterly earnings expectations",
    "content": (
        "TCS reported strong earnings this quarter, beating analyst "
        "consensus by a significant margin. Revenue rose 15% year-over-year."
    ),
    "source": "MockNews",
    "url": "https://example.com/tcs/earnings",
    "published_at": datetime(2024, 4, 25, tzinfo=timezone.utc).isoformat(),
}

BASE_META = {
    "symbol": "TCS",
    "company_name": "Tata Consultancy Services",
    "aliases": ["TCS", "Tata Consultancy"],
    "exchange": "NSE",
    "sector": "Technology",
    "industry": "IT Services",
    "market_cap_bucket": "LARGE",
}


class TestPipelineAnalyze:
    def test_basic_analyze_returns_200(self, client):
        res = client.post(
            "/api/pipeline/analyze",
            json={"news_item": BASE_NEWS, "stock_metadata": BASE_META},
        )
        assert res.status_code == 200

    def test_response_fields_present(self, client):
        res = client.post(
            "/api/pipeline/analyze",
            json={"news_item": BASE_NEWS, "stock_metadata": BASE_META},
        )
        data = res.json()
        expected_fields = [
            "news_id", "symbol", "relevant", "relevance_score",
            "event_type", "sentiment", "sentiment_score",
            "impact", "severity_label", "confidence",
            "evidence_strength", "action", "should_alert", "reason",
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    def test_symbol_matches_input(self, client):
        res = client.post(
            "/api/pipeline/analyze",
            json={"news_item": BASE_NEWS, "stock_metadata": BASE_META},
        )
        assert res.json()["symbol"] == "TCS"

    def test_severity_label_is_valid_string(self, client):
        res = client.post(
            "/api/pipeline/analyze",
            json={"news_item": BASE_NEWS, "stock_metadata": BASE_META},
        )
        assert res.json()["severity_label"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    def test_with_precomputed_ai_values(self, client):
        payload = {
            "news_item": BASE_NEWS,
            "stock_metadata": BASE_META,
            "ai_sentiment": "positive",
            "ai_sentiment_score": 0.92,
            "ai_event_type": "EARNINGS",
            "ai_impact": "HIGH",
            "ai_severity": "HIGH",
            "gemini_confidence": 0.85,
        }
        res = client.post("/api/pipeline/analyze", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["sentiment"] == "positive"

    def test_persist_alert_false_no_alert_id(self, client):
        res = client.post(
            "/api/pipeline/analyze",
            json={
                "news_item": BASE_NEWS,
                "stock_metadata": BASE_META,
                "persist_alert": False,
            },
        )
        assert res.status_code == 200
        assert res.json()["alert_id"] is None

    def test_missing_news_item_returns_422(self, client):
        res = client.post(
            "/api/pipeline/analyze",
            json={"stock_metadata": BASE_META},
        )
        assert res.status_code == 422

    def test_missing_stock_metadata_returns_422(self, client):
        res = client.post(
            "/api/pipeline/analyze",
            json={"news_item": BASE_NEWS},
        )
        assert res.status_code == 422

    def test_confidence_is_float_in_range(self, client):
        res = client.post(
            "/api/pipeline/analyze",
            json={"news_item": BASE_NEWS, "stock_metadata": BASE_META},
        )
        conf = res.json()["confidence"]
        assert isinstance(conf, float)
        assert 0.0 <= conf <= 1.0
