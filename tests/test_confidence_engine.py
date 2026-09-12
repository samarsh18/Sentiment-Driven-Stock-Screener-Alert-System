"""
tests/test_confidence_engine.py
--------------------------------
Unit tests for Historical Confidence Engine service.

All tests are 100% offline and deterministic.
"""

import pytest

from backend.app.services.confidence_engine import (
    ConfidenceEngine,
    ConfidenceResult,
    calculate_confidence,
)
from backend.app.services.event_statistics import EventStatisticsResult


def make_stats(
    horizon: str,
    n: int,
    pos: int,
    rate: float,
    mean_ret: float,
    med_ret: float = None,
    std_ret: float = 0.02,
    ci_lower: float = None,
    ci_upper: float = None,
) -> EventStatisticsResult:
    if med_ret is None:
        med_ret = mean_ret
    if ci_lower is None and n > 0:
        ci_lower = max(0.0, rate - 0.10)
    if ci_upper is None and n > 0:
        ci_upper = min(1.0, rate + 0.10)

    return EventStatisticsResult(
        horizon=horizon,
        sample_size=n,
        positive_count=pos,
        negative_count=n - pos,
        positive_rate=rate,
        positive_rate_ci_lower=ci_lower,
        positive_rate_ci_upper=ci_upper,
        mean_excess_return=mean_ret,
        median_excess_return=med_ret,
        std_excess_return=std_ret,
        min_excess_return=mean_ret - 0.05,
        max_excess_return=mean_ret + 0.05,
        sufficient_evidence=(n >= 30),
    )


class TestConfidenceEngine:
    def test_strong_positive_historical_evidence(self):
        s1d = make_stats("1D", n=50, pos=42, rate=0.84, mean_ret=0.06, ci_lower=0.74, ci_upper=0.92)
        s3d = make_stats("3D", n=50, pos=44, rate=0.88, mean_ret=0.08)
        s5d = make_stats("5D", n=50, pos=45, rate=0.90, mean_ret=0.10)

        res = calculate_confidence(stats_1d=s1d, stats_3d=s3d, stats_5d=s5d)

        assert res.historical_signal == "STRONG_POSITIVE"
        assert res.evidence_strength == "STRONG"
        assert res.confidence > 0.70
        assert res.sample_size_1d == 50

    def test_strong_negative_historical_evidence(self):
        s1d = make_stats("1D", n=50, pos=8, rate=0.16, mean_ret=-0.06, ci_lower=0.08, ci_upper=0.26)
        s3d = make_stats("3D", n=50, pos=6, rate=0.12, mean_ret=-0.08)
        s5d = make_stats("5D", n=50, pos=5, rate=0.10, mean_ret=-0.10)

        res = calculate_confidence(stats_1d=s1d, stats_3d=s3d, stats_5d=s5d)

        assert res.historical_signal == "STRONG_NEGATIVE"
        assert res.evidence_strength == "STRONG"
        assert res.confidence > 0.70

    def test_neutral_historical_evidence(self):
        s1d = make_stats("1D", n=50, pos=25, rate=0.50, mean_ret=0.0, ci_lower=0.36, ci_upper=0.64)
        res = calculate_confidence(stats_1d=s1d)

        assert res.historical_signal == "NEUTRAL"
        assert res.confidence <= 0.65

    def test_insufficient_sample_size(self):
        s1d = make_stats("1D", n=5, pos=4, rate=0.80, mean_ret=0.05)
        res = calculate_confidence(stats_1d=s1d)

        assert res.evidence_strength == "INSUFFICIENT"
        assert res.historical_signal == "INSUFFICIENT_DATA"
        assert res.confidence <= 0.35

    def test_wide_wilson_interval(self):
        # Wide interval (width = 0.60)
        s_wide = make_stats("1D", n=15, pos=8, rate=0.53, mean_ret=0.01, ci_lower=0.25, ci_upper=0.85)
        # Narrow interval (width = 0.16)
        s_narrow = make_stats("1D", n=15, pos=8, rate=0.53, mean_ret=0.01, ci_lower=0.45, ci_upper=0.61)

        res_wide = calculate_confidence(stats_1d=s_wide)
        res_narrow = calculate_confidence(stats_1d=s_narrow)

        assert res_wide.confidence < res_narrow.confidence

    def test_narrow_wilson_interval(self):
        s1d = make_stats("1D", n=100, pos=80, rate=0.80, mean_ret=0.05, ci_lower=0.72, ci_upper=0.86)
        res = calculate_confidence(stats_1d=s1d)

        assert res.evidence_strength == "STRONG"
        assert res.confidence >= 0.75

    def test_consistent_1d_3d_5d_direction(self):
        s1d = make_stats("1D", n=40, pos=30, rate=0.75, mean_ret=0.04)
        s3d = make_stats("3D", n=40, pos=32, rate=0.80, mean_ret=0.06)
        s5d = make_stats("5D", n=40, pos=34, rate=0.85, mean_ret=0.08)

        res = calculate_confidence(stats_1d=s1d, stats_3d=s3d, stats_5d=s5d)
        res_1d_only = calculate_confidence(stats_1d=s1d)

        assert res.confidence > res_1d_only.confidence

    def test_inconsistent_horizons(self):
        s1d = make_stats("1D", n=40, pos=30, rate=0.75, mean_ret=0.04)
        s3d = make_stats("3D", n=40, pos=18, rate=0.45, mean_ret=0.0)
        s5d = make_stats("5D", n=40, pos=10, rate=0.25, mean_ret=-0.04)

        res_inconsistent = calculate_confidence(stats_1d=s1d, stats_3d=s3d, stats_5d=s5d)
        res_1d_only = calculate_confidence(stats_1d=s1d)

        assert res_inconsistent.confidence < res_1d_only.confidence

    def test_high_volatility_penalty(self):
        s_low_vol = make_stats("1D", n=40, pos=30, rate=0.75, mean_ret=0.05, std_ret=0.02)
        s_high_vol = make_stats("1D", n=40, pos=30, rate=0.75, mean_ret=0.05, std_ret=0.15)

        res_low = calculate_confidence(stats_1d=s_low_vol)
        res_high = calculate_confidence(stats_1d=s_high_vol)

        assert res_high.confidence < res_low.confidence

    def test_gemini_high_confidence_weak_historical_evidence(self):
        # Sample size N=5 -> weak historical evidence
        s1d = make_stats("1D", n=5, pos=4, rate=0.80, mean_ret=0.05)

        # Gemini confidence = 0.99 (very high)
        res = calculate_confidence(stats_1d=s1d, gemini_confidence=0.99)

        # Capped at 0.35 due to N < 10 anti-overconfidence threshold
        assert res.confidence <= 0.35
        assert res.evidence_strength == "INSUFFICIENT"

    def test_strong_historical_evidence_weak_gemini_confidence(self):
        s1d = make_stats("1D", n=50, pos=40, rate=0.80, mean_ret=0.05)

        # Low Gemini confidence = 0.20
        res = calculate_confidence(stats_1d=s1d, gemini_confidence=0.20)

        # Historical evidence dominates -> confidence remains high (> 0.60)
        assert res.confidence > 0.60
        assert res.evidence_strength in ("STRONG", "MODERATE")

    def test_missing_3d_5d_statistics(self):
        s1d = make_stats("1D", n=35, pos=25, rate=0.71, mean_ret=0.03)

        res = calculate_confidence(stats_1d=s1d, stats_3d=None, stats_5d=None)

        assert res.sample_size_1d == 35
        assert res.sample_size_3d == 0
        assert res.sample_size_5d == 0
        assert res.confidence > 0.50

    def test_all_historical_data_missing(self):
        res = calculate_confidence(event_stats=None, gemini_confidence=0.95)

        assert res.confidence <= 0.35
        assert res.evidence_strength == "INSUFFICIENT"
        assert res.historical_signal == "INSUFFICIENT_DATA"

    def test_confidence_upper_caps(self):
        # N < 10 cap at 0.35
        s_small = make_stats("1D", n=8, pos=8, rate=1.0, mean_ret=0.10)
        res_small = calculate_confidence(stats_1d=s_small)
        assert res_small.confidence <= 0.35

        # 10 <= N < 30 cap at 0.55
        s_mid = make_stats("1D", n=20, pos=20, rate=1.0, mean_ret=0.10)
        res_mid = calculate_confidence(stats_1d=s_mid)
        assert res_mid.confidence <= 0.55

        # N >= 30 normal calculation allowed
        s_large = make_stats("1D", n=40, pos=40, rate=1.0, mean_ret=0.10)
        res_large = calculate_confidence(stats_1d=s_large)
        assert res_large.confidence > 0.55

    def test_output_contains_transparent_evidence_fields(self):
        s1d = make_stats("1D", n=40, pos=30, rate=0.75, mean_ret=0.04, ci_lower=0.60, ci_upper=0.88)
        res = calculate_confidence(stats_1d=s1d)

        assert isinstance(res.confidence, float)
        assert res.evidence_strength in ("STRONG", "MODERATE", "WEAK", "INSUFFICIENT")
        assert res.historical_signal in (
            "STRONG_POSITIVE", "MODERATE_POSITIVE", "NEUTRAL",
            "MODERATE_NEGATIVE", "STRONG_NEGATIVE", "INSUFFICIENT_DATA"
        )
        assert res.sample_size_1d == 40
        assert res.positive_rate_1d == 0.75
        assert res.positive_rate_ci_lower_1d == 0.60
        assert res.positive_rate_ci_upper_1d == 0.88
        assert res.mean_excess_return_1d == 0.04
        assert len(res.reason) > 0
