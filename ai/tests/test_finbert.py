from __future__ import annotations

import pytest

from ai.finbert import (
    DEFAULT_MAX_INPUT_CHARS,
    FinBertInferenceError,
    FinBertInvalidOutputError,
    FinBertSentimentAnalyzer,
    normalize_finbert_output,
)
from ai.schemas import SentimentResult


def test_positive_news_maps_to_positive_sentiment():
    analyzer = FinBertSentimentAnalyzer(
        predict_fn=lambda text: [{"label": "positive", "score": 0.93}]
    )
    result = analyzer.analyze("Acme beats earnings estimates")
    assert result == SentimentResult(sentiment="positive", sentiment_score=0.93)


def test_negative_news_maps_to_negative_sentiment_with_negative_score():
    analyzer = FinBertSentimentAnalyzer(
        predict_fn=lambda text: [{"label": "negative", "score": 0.81}]
    )
    result = analyzer.analyze("Acme misses guidance, shares plunge")
    assert result.sentiment == "negative"
    assert result.sentiment_score == pytest.approx(-0.81)


def test_neutral_news_has_zero_score_regardless_of_confidence():
    analyzer = FinBertSentimentAnalyzer(
        predict_fn=lambda text: [{"label": "neutral", "score": 0.6}]
    )
    result = analyzer.analyze("Acme announces annual shareholder meeting date")
    assert result == SentimentResult(sentiment="neutral", sentiment_score=0.0)


def test_empty_text_short_circuits_without_calling_model():
    calls = []

    def spy_predict(text: str):
        calls.append(text)
        return [{"label": "positive", "score": 0.9}]

    analyzer = FinBertSentimentAnalyzer(predict_fn=spy_predict)
    result = analyzer.analyze("   ")

    assert result == SentimentResult(sentiment="neutral", sentiment_score=0.0)
    assert calls == []  # model was never invoked


def test_extremely_long_text_is_truncated_before_model_call():
    seen = {}

    def spy_predict(text: str):
        seen["length"] = len(text)
        return [{"label": "neutral", "score": 0.5}]

    long_text = "A" * (DEFAULT_MAX_INPUT_CHARS * 3)
    analyzer = FinBertSentimentAnalyzer(predict_fn=spy_predict)
    analyzer.analyze(long_text)

    assert seen["length"] == DEFAULT_MAX_INPUT_CHARS


def test_model_runtime_error_raises_inference_error():
    def failing_predict(text: str):
        raise RuntimeError("CUDA out of memory")

    analyzer = FinBertSentimentAnalyzer(predict_fn=failing_predict)
    with pytest.raises(FinBertInferenceError):
        analyzer.analyze("Some financial news")


@pytest.mark.parametrize(
    "raw_output",
    [
        [],  # empty list
        [{"label": "bullish", "score": 0.9}],  # unexpected label
        [{"label": "positive"}],  # missing score
        [{"score": 0.9}],  # missing label
        [{"label": "positive", "score": "high"}],  # non-numeric score
        [{"label": "positive", "score": 1.5}],  # out-of-range score
        None,  # malformed shape entirely
    ],
)
def test_invalid_model_output_raises_invalid_output_error(raw_output):
    with pytest.raises(FinBertInvalidOutputError):
        normalize_finbert_output(raw_output)
