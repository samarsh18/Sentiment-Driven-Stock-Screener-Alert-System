"""
Deterministic decision engine.

This is plain, testable Python logic — NOT an LLM call. It takes the
already-validated Gemini analysis (plus optional per-user preferences) and
classifies the news into one of four actions:

    RISK_ALERT | OPPORTUNITY | WATCH | INFORMATIONAL

and decides whether it crosses the user's configured alert threshold.

Thresholds are configurable via `DecisionThresholds` (defaults match the
project spec) rather than hardcoded magic numbers, and the "should this
user actually be alerted" logic is kept fully separate from both the
model output and the classification rule, per the project's requirement
that severity-threshold logic stay independent of the model.
"""

from __future__ import annotations

from dataclasses import dataclass

from ai.schemas import Action, DecisionResult, GeminiAnalysis, UserAlertPreferences


@dataclass(frozen=True)
class DecisionThresholds:
    """Configurable thresholds for the decision engine's classification rule.

    Defaults match the project's example:
        sentiment == negative AND severity >= risk_alert_min_severity -> RISK_ALERT
        sentiment == positive AND severity >= opportunity_min_severity -> OPPORTUNITY
        impact == "high" -> WATCH
        otherwise -> INFORMATIONAL
    """

    risk_alert_min_severity: int = 8
    opportunity_min_severity: int = 8
    watch_impact_level: str = "high"


DEFAULT_THRESHOLDS = DecisionThresholds()


def classify_action(analysis: GeminiAnalysis, thresholds: DecisionThresholds = DEFAULT_THRESHOLDS) -> Action:
    """Pure classification rule -> one of the four actions. No side effects,
    no alerting logic, no LLM calls."""
    if analysis.sentiment == "negative" and analysis.severity >= thresholds.risk_alert_min_severity:
        return "RISK_ALERT"
    if analysis.sentiment == "positive" and analysis.severity >= thresholds.opportunity_min_severity:
        return "OPPORTUNITY"
    if analysis.impact == thresholds.watch_impact_level:
        return "WATCH"
    return "INFORMATIONAL"


def should_alert_user(analysis: GeminiAnalysis, user_prefs: UserAlertPreferences) -> bool:
    """Whether this specific user's minimum-severity preference is met.

    Kept fully independent of the model and of `classify_action`: a user
    can choose to only be notified above a personal severity bar,
    regardless of which action bucket the news falls into.
    """
    return analysis.severity >= user_prefs.min_severity


def _build_message(action: Action, analysis: GeminiAnalysis) -> str:
    prefixes = {
        "RISK_ALERT": f"Risk alert for {analysis.symbol}",
        "OPPORTUNITY": f"Opportunity signal for {analysis.symbol}",
        "WATCH": f"Watch item for {analysis.symbol}",
        "INFORMATIONAL": f"Informational update for {analysis.symbol}",
    }
    return f"{prefixes[action]}: {analysis.summary}"


def evaluate(
    analysis: GeminiAnalysis,
    user_prefs: UserAlertPreferences | None = None,
    thresholds: DecisionThresholds = DEFAULT_THRESHOLDS,
) -> DecisionResult:
    """Runs the full deterministic decision step for one validated Gemini
    analysis, producing the final DecisionResult.

    `user_prefs` defaults to `min_severity=1` (i.e. alert on anything) if
    not supplied, since not every caller will have a user context (e.g.
    a system-wide dashboard feed rather than a personal alert).
    """
    effective_prefs = user_prefs or UserAlertPreferences()

    action = classify_action(analysis, thresholds)
    should_alert = should_alert_user(analysis, effective_prefs)
    message = _build_message(action, analysis)

    return DecisionResult(
        news_id=analysis.news_id,
        symbol=analysis.symbol,
        action=action,
        should_alert=should_alert,
        severity=analysis.severity,
        message=message,
    )
