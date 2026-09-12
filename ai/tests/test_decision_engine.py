from __future__ import annotations

from ai.decision_engine import DecisionThresholds, classify_action, evaluate
from ai.schemas import GeminiAnalysis, UserAlertPreferences


def _analysis(**overrides) -> GeminiAnalysis:
    base = dict(
        news_id="news-001",
        symbol="ACME",
        sentiment="neutral",
        sentiment_score=0.0,
        impact="low",
        severity=1,
        confidence=0.5,
        reason="Routine filing.",
        summary="Acme filed a routine 10-Q.",
    )
    base.update(overrides)
    return GeminiAnalysis(**base)


def test_high_severity_negative_sentiment_triggers_risk_alert():
    analysis = _analysis(sentiment="negative", severity=9, impact="high")
    assert classify_action(analysis) == "RISK_ALERT"


def test_high_severity_positive_sentiment_triggers_opportunity():
    analysis = _analysis(sentiment="positive", severity=8, impact="medium")
    assert classify_action(analysis) == "OPPORTUNITY"


def test_high_impact_alone_triggers_watch():
    analysis = _analysis(sentiment="neutral", severity=3, impact="high")
    assert classify_action(analysis) == "WATCH"


def test_low_severity_low_impact_is_informational():
    analysis = _analysis(sentiment="positive", severity=2, impact="low")
    assert classify_action(analysis) == "INFORMATIONAL"


def test_negative_sentiment_below_threshold_does_not_trigger_risk_alert():
    analysis = _analysis(sentiment="negative", severity=5, impact="medium")
    assert classify_action(analysis) != "RISK_ALERT"


def test_thresholds_are_configurable():
    analysis = _analysis(sentiment="negative", severity=6, impact="medium")
    lenient = DecisionThresholds(risk_alert_min_severity=5)
    assert classify_action(analysis, thresholds=lenient) == "RISK_ALERT"


def test_user_severity_threshold_blocks_alert_below_minimum():
    analysis = _analysis(sentiment="negative", severity=5, impact="medium")
    prefs = UserAlertPreferences(min_severity=7)
    decision = evaluate(analysis, user_prefs=prefs)
    assert decision.should_alert is False


def test_user_severity_threshold_allows_alert_at_or_above_minimum():
    analysis = _analysis(sentiment="negative", severity=8, impact="high")
    prefs = UserAlertPreferences(min_severity=7)
    decision = evaluate(analysis, user_prefs=prefs)
    assert decision.should_alert is True
    assert decision.action == "RISK_ALERT"


def test_default_user_prefs_alert_on_anything():
    analysis = _analysis(sentiment="positive", severity=1, impact="low")
    decision = evaluate(analysis)
    assert decision.should_alert is True


def test_decision_result_carries_through_news_id_and_symbol():
    analysis = _analysis(news_id="news-42", symbol="TSLA", severity=9, sentiment="negative")
    decision = evaluate(analysis)
    assert decision.news_id == "news-42"
    assert decision.symbol == "TSLA"
