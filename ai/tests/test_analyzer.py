from __future__ import annotations

import json

from ai.analyzer import analyze_news
from ai.finbert import FinBertSentimentAnalyzer
from ai.gemini import GeminiClient
from ai.schemas import UserAlertPreferences


def _gemini_payload(news, **overrides) -> dict:
    payload = {
        "news_id": news.news_id,
        "symbol": news.symbol,
        "sentiment": "negative",
        "sentiment_score": -0.8,
        "impact": "high",
        "severity": 9,
        "confidence": 0.9,
        "reason": "Guidance cut sharply below prior estimates.",
        "summary": "Acme cut full-year guidance, citing weak demand.",
    }
    payload.update(overrides)
    return payload


def _make_pipeline(sample_news, finbert_label="negative", finbert_score=0.8, gemini_overrides=None):
    finbert = FinBertSentimentAnalyzer(
        predict_fn=lambda text: [{"label": finbert_label, "score": finbert_score}]
    )
    payload = _gemini_payload(sample_news, **(gemini_overrides or {}))
    gemini = GeminiClient(api_key="unused", generate_fn=lambda prompt: json.dumps(payload))
    return finbert, gemini


def test_full_pipeline_produces_risk_alert(sample_news):
    finbert, gemini = _make_pipeline(sample_news)
    result = analyze_news(sample_news, finbert, gemini)

    assert result.success is True
    assert result.sentiment_result.sentiment == "negative"
    assert result.gemini_analysis.impact == "high"
    assert result.decision.action == "RISK_ALERT"
    assert result.decision.should_alert is True
    assert result.sentiment_degraded is False


def test_full_pipeline_respects_user_min_severity(sample_news):
    finbert, gemini = _make_pipeline(sample_news, gemini_overrides={"severity": 4, "sentiment": "negative"})
    prefs = UserAlertPreferences(min_severity=7)

    result = analyze_news(sample_news, finbert, gemini, user_prefs=prefs)

    assert result.success is True
    assert result.decision.should_alert is False


def test_finbert_failure_falls_back_to_neutral_but_pipeline_continues(sample_news):
    def failing_predict(text: str):
        raise RuntimeError("model unavailable")

    finbert = FinBertSentimentAnalyzer(predict_fn=failing_predict)
    payload = _gemini_payload(sample_news, sentiment="neutral", severity=2, impact="low")
    gemini = GeminiClient(api_key="unused", generate_fn=lambda prompt: json.dumps(payload))

    result = analyze_news(sample_news, finbert, gemini)

    assert result.success is True
    assert result.sentiment_degraded is True
    assert result.sentiment_result.sentiment == "neutral"
    assert result.sentiment_result.sentiment_score == 0.0


def test_gemini_failure_marks_pipeline_unsuccessful(sample_news):
    finbert = FinBertSentimentAnalyzer(
        predict_fn=lambda text: [{"label": "neutral", "score": 0.5}]
    )
    gemini = GeminiClient(api_key="unused", generate_fn=lambda prompt: "not json")

    result = analyze_news(sample_news, finbert, gemini)

    assert result.success is False
    assert result.decision is None
    assert result.gemini_analysis is None
    assert result.error is not None


def test_positive_high_severity_yields_opportunity(sample_news):
    finbert, gemini = _make_pipeline(
        sample_news,
        finbert_label="positive",
        finbert_score=0.85,
        gemini_overrides={"sentiment": "positive", "sentiment_score": 0.85, "severity": 9, "impact": "high"},
    )
    result = analyze_news(sample_news, finbert, gemini)
    assert result.decision.action == "OPPORTUNITY"


def test_high_impact_low_severity_yields_watch(sample_news):
    finbert, gemini = _make_pipeline(
        sample_news,
        finbert_label="neutral",
        finbert_score=0.5,
        gemini_overrides={"sentiment": "neutral", "sentiment_score": 0.0, "severity": 3, "impact": "high"},
    )
    result = analyze_news(sample_news, finbert, gemini)
    assert result.decision.action == "WATCH"


def test_low_everything_yields_informational(sample_news):
    finbert, gemini = _make_pipeline(
        sample_news,
        finbert_label="neutral",
        finbert_score=0.5,
        gemini_overrides={"sentiment": "neutral", "sentiment_score": 0.0, "severity": 2, "impact": "low"},
    )
    result = analyze_news(sample_news, finbert, gemini)
    assert result.decision.action == "INFORMATIONAL"
