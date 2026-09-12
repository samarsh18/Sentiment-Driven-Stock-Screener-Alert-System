"""
tests/test_event_statistics.py
-------------------------------
Unit tests for Event Statistics & Wilson Confidence Interval service.

All tests are 100% offline and deterministic.
"""

import math
import pytest
from datetime import datetime, timezone

from backend.app.services.event_statistics import (
    EventStatisticsResult,
    calculate_event_statistics,
    calculate_horizon_statistics,
    calculate_wilson_score_interval,
)
from backend.app.services.event_study import EventStudyResult


def make_study(
    news_id: str,
    r1d: float = None,
    r3d: float = None,
    r5d: float = None,
) -> EventStudyResult:
    return EventStudyResult(
        news_id=news_id,
        symbol="RELIANCE",
        exchange="NSE",
        event_date=datetime(2024, 4, 1, tzinfo=timezone.utc),
        excess_return_1d=r1d,
        excess_return_3d=r3d,
        excess_return_5d=r5d,
    )


class TestEventStatistics:
    def test_all_positive_returns(self):
        returns = [0.05, 0.08, 0.12, 0.03, 0.15]
        stats = calculate_horizon_statistics(returns, horizon="1D", min_sample_size=5)

        assert stats.sample_size == 5
        assert stats.positive_count == 5
        assert stats.negative_count == 0
        assert stats.positive_rate == 1.0
        assert stats.mean_excess_return == pytest.approx(0.086)
        assert stats.min_excess_return == 0.03
        assert stats.max_excess_return == 0.15
        assert stats.positive_rate_ci_lower > 0.40
        assert stats.positive_rate_ci_upper == 1.0
        assert stats.sufficient_evidence is True

    def test_all_negative_returns(self):
        returns = [-0.05, -0.02, -0.10, -0.01]
        stats = calculate_horizon_statistics(returns, horizon="3D", min_sample_size=4)

        assert stats.sample_size == 4
        assert stats.positive_count == 0
        assert stats.negative_count == 4
        assert stats.positive_rate == 0.0
        assert stats.mean_excess_return == pytest.approx(-0.045)
        assert stats.positive_rate_ci_lower == 0.0
        assert stats.positive_rate_ci_upper < 0.60
        assert stats.sufficient_evidence is True

    def test_mixed_returns(self):
        returns = [0.05, -0.02, 0.08, -0.04, 0.01]
        stats = calculate_horizon_statistics(returns, horizon="5D", min_sample_size=5)

        assert stats.sample_size == 5
        assert stats.positive_count == 3
        assert stats.negative_count == 2
        assert stats.positive_rate == pytest.approx(0.60)
        assert stats.median_excess_return == 0.01
        assert stats.sufficient_evidence is True

    def test_zero_returns(self):
        # 0.0 is not positive and not negative
        returns = [0.05, 0.0, -0.02, 0.0]
        stats = calculate_horizon_statistics(returns, horizon="1D", min_sample_size=4)

        assert stats.sample_size == 4
        assert stats.positive_count == 1
        assert stats.negative_count == 1
        assert stats.positive_rate == 0.25
        assert stats.sufficient_evidence is True

    def test_missing_returns(self):
        studies = [
            make_study("N1", r1d=0.05, r3d=0.10, r5d=None),
            make_study("N2", r1d=0.02, r3d=None, r5d=0.04),
            make_study("N3", r1d=None, r3d=-0.03, r5d=-0.05),
        ]

        res = calculate_event_statistics(studies, min_sample_size=2)

        assert res["1D"].sample_size == 2
        assert res["3D"].sample_size == 2
        assert res["5D"].sample_size == 2
        assert res["1D"].positive_count == 2
        assert res["3D"].positive_count == 1
        assert res["5D"].positive_count == 1

    def test_empty_input(self):
        res = calculate_event_statistics([], min_sample_size=10)

        for horizon in ["1D", "3D", "5D"]:
            stats = res[horizon]
            assert stats.sample_size == 0
            assert stats.positive_count == 0
            assert stats.negative_count == 0
            assert stats.positive_rate is None
            assert stats.positive_rate_ci_lower is None
            assert stats.positive_rate_ci_upper is None
            assert stats.mean_excess_return is None
            assert stats.median_excess_return is None
            assert stats.std_excess_return is None
            assert stats.min_excess_return is None
            assert stats.max_excess_return is None
            assert stats.sufficient_evidence is False

    def test_1d_statistics(self):
        studies = [
            make_study("N1", r1d=0.04),
            make_study("N2", r1d=0.06),
            make_study("N3", r1d=-0.02),
        ]
        res = calculate_event_statistics(studies, min_sample_size=3)

        s1d = res["1D"]
        assert s1d.horizon == "1D"
        assert s1d.sample_size == 3
        assert s1d.mean_excess_return == pytest.approx(0.026667, abs=1e-4)

    def test_3d_statistics(self):
        studies = [
            make_study("N1", r3d=0.10),
            make_study("N2", r3d=0.15),
            make_study("N3", r3d=0.05),
        ]
        res = calculate_event_statistics(studies, min_sample_size=3)

        s3d = res["3D"]
        assert s3d.horizon == "3D"
        assert s3d.sample_size == 3
        assert s3d.positive_rate == 1.0
        assert s3d.median_excess_return == 0.10

    def test_5d_statistics(self):
        studies = [
            make_study("N1", r5d=-0.10),
            make_study("N2", r5d=-0.05),
            make_study("N3", r5d=0.02),
        ]
        res = calculate_event_statistics(studies, min_sample_size=3)

        s5d = res["5D"]
        assert s5d.horizon == "5D"
        assert s5d.sample_size == 3
        assert s5d.min_excess_return == -0.10
        assert s5d.max_excess_return == 0.02

    def test_wilson_interval_correctness(self):
        # Test 10/10 successes -> lower bound should be > 0.70 and upper bound 1.0
        lower, upper = calculate_wilson_score_interval(10, 10)
        assert lower is not None and upper is not None
        assert 0.70 < lower < 0.75
        assert upper == 1.0

        # Test 0/10 successes -> lower bound 0.0, upper bound < 0.30
        lower0, upper0 = calculate_wilson_score_interval(0, 10)
        assert lower0 == 0.0
        assert 0.25 < upper0 < 0.30

        # Test 50/100 successes -> symmetric around 0.50
        lower50, upper50 = calculate_wilson_score_interval(50, 100)
        assert 0.40 < lower50 < 0.41
        assert 0.59 < upper50 < 0.60

    def test_insufficient_evidence_handling(self):
        studies = [make_study(f"N{i}", r1d=0.05) for i in range(5)]
        res = calculate_event_statistics(studies, min_sample_size=30)

        s1d = res["1D"]
        assert s1d.sample_size == 5
        assert s1d.sufficient_evidence is False
        assert s1d.positive_rate == 1.0
