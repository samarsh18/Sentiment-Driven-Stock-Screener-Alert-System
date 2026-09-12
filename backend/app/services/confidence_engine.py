"""
backend/app/services/confidence_engine.py
-------------------------------------------
Historical Confidence Engine Service.

Calculates a transparent, evidence-based confidence score and historical signal
for a target news event by evaluating historical event statistics (1D, 3D, 5D)
alongside bounded AI sentiment/confidence inputs.

Primary Rule: Historical evidence dominates when sufficient data exists.
AI LLM confidence cannot override historical sample size limits or weak evidence.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Union

from pydantic import BaseModel

from backend.app.services.event_statistics import EventStatisticsResult

logger = logging.getLogger(__name__)


class ConfidenceResult(BaseModel):
    """
    Transparent, evidence-based confidence result.
    """

    confidence: float
    evidence_strength: str  # STRONG, MODERATE, WEAK, INSUFFICIENT
    sample_size_1d: int = 0
    sample_size_3d: int = 0
    sample_size_5d: int = 0
    positive_rate_1d: Optional[float] = None
    positive_rate_ci_lower_1d: Optional[float] = None
    positive_rate_ci_upper_1d: Optional[float] = None
    median_excess_return_1d: Optional[float] = None
    mean_excess_return_1d: Optional[float] = None
    historical_signal: str  # STRONG_POSITIVE, MODERATE_POSITIVE, NEUTRAL, MODERATE_NEGATIVE, STRONG_NEGATIVE, INSUFFICIENT_DATA
    reason: str

    model_config = {
        "extra": "forbid",
        "arbitrary_types_allowed": True,
    }


class ConfidenceEngine:
    """
    Deterministic scoring engine that combines historical statistics with AI analysis
    under strict anti-overconfidence sample-size caps.

    Configurable Constants
    ----------------------
    MIN_SAMPLE_LOW : int (default 10)
        Below this sample size, evidence is INSUFFICIENT and capped at CAP_LOW_SAMPLE.
    MIN_SAMPLE_NORMAL : int (default 30)
        Below this sample size, confidence is capped at CAP_MID_SAMPLE.
    MIN_SAMPLE_STRONG : int (default 100)
        Sample size required for potential STRONG evidence classification with narrow CI.
    CAP_LOW_SAMPLE : float (default 0.35)
        Maximum confidence allowed when N < MIN_SAMPLE_LOW.
    CAP_MID_SAMPLE : float (default 0.55)
        Maximum confidence allowed when MIN_SAMPLE_LOW <= N < MIN_SAMPLE_NORMAL.
    WEIGHT_SAMPLE : float (default 0.40)
        Weight assigned to sample size relative to target.
    WEIGHT_WILSON : float (default 0.30)
        Weight assigned to Wilson interval precision (1 - width).
    WEIGHT_RATE_DEV : float (default 0.30)
        Weight assigned to directional rate magnitude.
    MAX_AI_ADJUSTMENT : float (default 0.15)
        Maximum absolute adjustment (+/-) allowed from AI confidence/sentiment.
    """

    MIN_SAMPLE_LOW: int = 10
    MIN_SAMPLE_NORMAL: int = 30
    MIN_SAMPLE_STRONG: int = 100

    CAP_LOW_SAMPLE: float = 0.35
    CAP_MID_SAMPLE: float = 0.55

    WEIGHT_SAMPLE: float = 0.40
    WEIGHT_WILSON: float = 0.30
    WEIGHT_RATE_DEV: float = 0.30

    TARGET_SAMPLE_SIZE: int = 50
    MAX_AI_ADJUSTMENT: float = 0.15

    def __init__(
        self,
        min_sample_low: int = 10,
        min_sample_normal: int = 30,
        min_sample_strong: int = 100,
        cap_low_sample: float = 0.35,
        cap_mid_sample: float = 0.55,
        max_ai_adjustment: float = 0.15,
    ) -> None:
        self.MIN_SAMPLE_LOW = min_sample_low
        self.MIN_SAMPLE_NORMAL = min_sample_normal
        self.MIN_SAMPLE_STRONG = min_sample_strong
        self.CAP_LOW_SAMPLE = cap_low_sample
        self.CAP_MID_SAMPLE = cap_mid_sample
        self.MAX_AI_ADJUSTMENT = max_ai_adjustment

    def calculate_confidence(
        self,
        event_stats: Optional[Dict[str, EventStatisticsResult]] = None,
        stats_1d: Optional[EventStatisticsResult] = None,
        stats_3d: Optional[EventStatisticsResult] = None,
        stats_5d: Optional[EventStatisticsResult] = None,
        gemini_confidence: Optional[float] = None,
        finbert_score: Optional[float] = None,
        gemini_severity: Optional[Union[str, float]] = None,
    ) -> ConfidenceResult:
        """
        Calculate deterministic confidence score and evidence summary.
        """
        # Resolve horizon stats
        s1d = stats_1d or (event_stats.get("1D") if event_stats else None)
        s3d = stats_3d or (event_stats.get("3D") if event_stats else None)
        s5d = stats_5d or (event_stats.get("5D") if event_stats else None)

        n1d = s1d.sample_size if s1d else 0
        n3d = s3d.sample_size if s3d else 0
        n5d = s5d.sample_size if s5d else 0

        p1d = s1d.positive_rate if s1d else None
        ci_lower_1d = s1d.positive_rate_ci_lower if s1d else None
        ci_upper_1d = s1d.positive_rate_ci_upper if s1d else None
        med_1d = s1d.median_excess_return if s1d else None
        mean_1d = s1d.mean_excess_return if s1d else None
        std_1d = s1d.std_excess_return if s1d else None

        max_n = max(n1d, n3d, n5d)

        # Handle zero or completely insufficient data
        if max_n == 0 or n1d == 0:
            return ConfidenceResult(
                confidence=round(min(0.20, self.CAP_LOW_SAMPLE), 4),
                evidence_strength="INSUFFICIENT",
                sample_size_1d=n1d,
                sample_size_3d=n3d,
                sample_size_5d=n5d,
                positive_rate_1d=p1d,
                positive_rate_ci_lower_1d=ci_lower_1d,
                positive_rate_ci_upper_1d=ci_upper_1d,
                median_excess_return_1d=med_1d,
                mean_excess_return_1d=mean_1d,
                historical_signal="INSUFFICIENT_DATA",
                reason=f"Insufficient historical observations across all horizons (N1D={n1d}).",
            )

        # Determine Historical Signal
        historical_signal = self._determine_signal(n1d, p1d, mean_1d)

        # 1. Sample size component
        sample_score = min(1.0, n1d / float(self.TARGET_SAMPLE_SIZE))

        # 2. Wilson CI precision component (1 - width)
        if ci_lower_1d is not None and ci_upper_1d is not None:
            ci_width = max(0.0, ci_upper_1d - ci_lower_1d)
            wilson_score = max(0.0, 1.0 - ci_width)
        else:
            ci_width = 1.0
            wilson_score = 0.0

        # 3. Directional deviation component
        rate_dev_score = abs(p1d - 0.5) * 2.0 if p1d is not None else 0.0

        # Base Historical Evidence Score
        base_hist = (
            self.WEIGHT_SAMPLE * sample_score +
            self.WEIGHT_WILSON * wilson_score +
            self.WEIGHT_RATE_DEV * rate_dev_score
        )

        # 4. Multi-horizon consistency adjustment
        horizon_bonus = self._calculate_horizon_consistency(s1d, s3d, s5d)

        # 5. Effect magnitude adjustment
        magnitude_bonus = 0.0
        if mean_1d is not None:
            magnitude_bonus = min(0.15, (abs(mean_1d) / 0.10) * 0.15)

        # 6. Volatility penalty
        volatility_penalty = 0.0
        if std_1d is not None and std_1d > 0.05:
            volatility_penalty = min(0.20, (std_1d - 0.05) * 2.0)

        hist_evidence_score = max(0.0, min(1.0, base_hist + horizon_bonus + magnitude_bonus - volatility_penalty))

        # 7. AI Evidence Adjustment (bounded by MAX_AI_ADJUSTMENT)
        ai_adj = self._calculate_ai_adjustment(gemini_confidence, finbert_score, gemini_severity, p1d)

        raw_confidence = hist_evidence_score + ai_adj

        # 8. Anti-Overconfidence Sample Size Capping Policy
        if n1d < self.MIN_SAMPLE_LOW:
            final_confidence = min(raw_confidence, self.CAP_LOW_SAMPLE)
            evidence_strength = "INSUFFICIENT"
            reason_cap = f"Sample size N1D={n1d} < {self.MIN_SAMPLE_LOW}; confidence capped at {self.CAP_LOW_SAMPLE}."
        elif n1d < self.MIN_SAMPLE_NORMAL:
            final_confidence = min(raw_confidence, self.CAP_MID_SAMPLE)
            evidence_strength = "WEAK"
            reason_cap = f"Moderate sample size N1D={n1d} < {self.MIN_SAMPLE_NORMAL}; confidence capped at {self.CAP_MID_SAMPLE}."
        else:
            final_confidence = max(0.0, min(1.0, raw_confidence))
            if n1d >= self.MIN_SAMPLE_STRONG and final_confidence >= 0.70 and ci_width <= 0.35:
                evidence_strength = "STRONG"
            elif final_confidence >= 0.60:
                evidence_strength = "MODERATE" if n1d < 50 else "STRONG"
            elif final_confidence >= 0.45:
                evidence_strength = "MODERATE"
            else:
                evidence_strength = "WEAK"
            reason_cap = f"Sufficient sample size N1D={n1d}."

        reason_text = (
            f"{reason_cap} Historical signal: {historical_signal} (Rate 1D={p1d}, Mean 1D={mean_1d}, CI width={round(ci_width, 4)}). "
            f"Base hist score={round(hist_evidence_score, 4)}, AI adj={round(ai_adj, 4)}."
        )

        return ConfidenceResult(
            confidence=round(final_confidence, 4),
            evidence_strength=evidence_strength,
            sample_size_1d=n1d,
            sample_size_3d=n3d,
            sample_size_5d=n5d,
            positive_rate_1d=p1d,
            positive_rate_ci_lower_1d=ci_lower_1d,
            positive_rate_ci_upper_1d=ci_upper_1d,
            median_excess_return_1d=med_1d,
            mean_excess_return_1d=mean_1d,
            historical_signal=historical_signal,
            reason=reason_text,
        )

    def _determine_signal(self, n1d: int, p1d: Optional[float], mean_1d: Optional[float]) -> str:
        """Classify historical signal into standard categories."""
        if n1d < self.MIN_SAMPLE_LOW or p1d is None or mean_1d is None:
            return "INSUFFICIENT_DATA"
        if p1d >= 0.70 and mean_1d > 0.01:
            return "STRONG_POSITIVE"
        if p1d >= 0.55 and mean_1d > 0.0:
            return "MODERATE_POSITIVE"
        if p1d <= 0.30 and mean_1d < -0.01:
            return "STRONG_NEGATIVE"
        if p1d <= 0.45 and mean_1d < 0.0:
            return "MODERATE_NEGATIVE"
        return "NEUTRAL"

    def _calculate_horizon_consistency(
        self,
        s1d: Optional[EventStatisticsResult],
        s3d: Optional[EventStatisticsResult],
        s5d: Optional[EventStatisticsResult],
    ) -> float:
        """Evaluate directional consistency across available 1D, 3D, 5D horizons."""
        rates = []
        for s in (s1d, s3d, s5d):
            if s and s.sample_size > 0 and s.positive_rate is not None:
                rates.append(s.positive_rate)

        if len(rates) < 2:
            return 0.0

        all_pos = all(r >= 0.55 for r in rates)
        all_neg = all(r <= 0.45 for r in rates)

        if all_pos or all_neg:
            return 0.15  # Consistent direction bonus

        # Check conflicting directions (e.g. 1D high positive but 5D high negative)
        if (rates[0] >= 0.60 and rates[-1] <= 0.40) or (rates[0] <= 0.40 and rates[-1] >= 0.60):
            return -0.10  # Conflict penalty

        return 0.0

    def _calculate_ai_adjustment(
        self,
        gemini_confidence: Optional[float],
        finbert_score: Optional[float],
        gemini_severity: Optional[Union[str, float]],
        p1d: Optional[float],
    ) -> float:
        """
        Calculate bounded AI evidence adjustment.
        AI inputs cannot adjust the score by more than +/- MAX_AI_ADJUSTMENT.
        """
        if gemini_confidence is None and finbert_score is None:
            return 0.0

        adj = 0.0

        if gemini_confidence is not None:
            g_conf = max(0.0, min(1.0, float(gemini_confidence)))
            adj += (g_conf - 0.5) * 0.10

        if finbert_score is not None and p1d is not None:
            f_score = max(-1.0, min(1.0, float(finbert_score)))
            # If FinBERT sentiment aligns with historical positive rate
            if (f_score > 0 and p1d >= 0.50) or (f_score < 0 and p1d <= 0.50):
                adj += 0.05
            else:
                adj -= 0.05

        return max(-self.MAX_AI_ADJUSTMENT, min(self.MAX_AI_ADJUSTMENT, adj))


def calculate_confidence(
    event_stats: Optional[Dict[str, EventStatisticsResult]] = None,
    stats_1d: Optional[EventStatisticsResult] = None,
    stats_3d: Optional[EventStatisticsResult] = None,
    stats_5d: Optional[EventStatisticsResult] = None,
    gemini_confidence: Optional[float] = None,
    finbert_score: Optional[float] = None,
    gemini_severity: Optional[Union[str, float]] = None,
) -> ConfidenceResult:
    """
    Convenience function to calculate confidence result.
    """
    engine = ConfidenceEngine()
    return engine.calculate_confidence(
        event_stats=event_stats,
        stats_1d=stats_1d,
        stats_3d=stats_3d,
        stats_5d=stats_5d,
        gemini_confidence=gemini_confidence,
        finbert_score=finbert_score,
        gemini_severity=gemini_severity,
    )
