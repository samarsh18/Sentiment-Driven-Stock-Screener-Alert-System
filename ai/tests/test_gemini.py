from __future__ import annotations

import json

import pytest

from ai.gemini import GeminiClient, GeminiConfigError, GeminiOutputError, GeminiRequestError
from ai.schemas import SentimentResult


def _valid_payload(news) -> dict:
    return {
        "news_id": news.news_id,
        "symbol": news.symbol,
        "sentiment": "positive",
        "sentiment_score": 0.7,
        "impact": "high",
        "severity": 9,
        "confidence": 0.85,
        "reason": "Revenue and guidance both beat expectations.",
        "summary": "Acme beat Q3 estimates and raised full-year guidance.",
    }


def test_gemini_success_returns_validated_analysis(sample_news):
    payload = _valid_payload(sample_news)
    client = GeminiClient(api_key="unused", generate_fn=lambda prompt: json.dumps(payload))

    result = client.analyze(sample_news, SentimentResult(sentiment="positive", sentiment_score=0.7))

    assert result.news_id == sample_news.news_id
    assert result.symbol == sample_news.symbol
    assert result.impact == "high"
    assert result.severity == 9


def test_gemini_strips_markdown_code_fences(sample_news):
    payload = _valid_payload(sample_news)
    fenced = f"```json\n{json.dumps(payload)}\n```"
    client = GeminiClient(api_key="unused", generate_fn=lambda prompt: fenced)

    result = client.analyze(sample_news, SentimentResult(sentiment="positive", sentiment_score=0.7))
    assert result.severity == 9


def test_gemini_request_failure_raises_request_error(sample_news):
    def failing_generate(prompt: str):
        raise ConnectionError("timeout")

    client = GeminiClient(api_key="unused", generate_fn=failing_generate)

    with pytest.raises(GeminiRequestError):
        client.analyze(sample_news, SentimentResult(sentiment="neutral", sentiment_score=0.0))


def test_gemini_non_json_output_raises_output_error(sample_news):
    client = GeminiClient(api_key="unused", generate_fn=lambda prompt: "not json at all")

    with pytest.raises(GeminiOutputError):
        client.analyze(sample_news, SentimentResult(sentiment="neutral", sentiment_score=0.0))


def test_gemini_malformed_output_missing_fields_raises_output_error(sample_news):
    incomplete_payload = {"news_id": sample_news.news_id, "symbol": sample_news.symbol}
    client = GeminiClient(api_key="unused", generate_fn=lambda prompt: json.dumps(incomplete_payload))

    with pytest.raises(GeminiOutputError):
        client.analyze(sample_news, SentimentResult(sentiment="neutral", sentiment_score=0.0))


def test_gemini_malformed_output_out_of_range_severity_raises_output_error(sample_news):
    payload = _valid_payload(sample_news)
    payload["severity"] = 99  # out of 1-10 range
    client = GeminiClient(api_key="unused", generate_fn=lambda prompt: json.dumps(payload))

    with pytest.raises(GeminiOutputError):
        client.analyze(sample_news, SentimentResult(sentiment="neutral", sentiment_score=0.0))


def test_gemini_requires_api_key_when_no_generate_fn_injected(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(GeminiConfigError):
        GeminiClient()


def test_gemini_reads_api_key_from_environment(monkeypatch, sample_news):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
    payload = _valid_payload(sample_news)
    client = GeminiClient(generate_fn=lambda prompt: json.dumps(payload))
    assert client._api_key == "fake-key-for-test"
