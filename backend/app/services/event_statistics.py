"""
backend/app/services/event_statistics.py
-----------------------------------------
Event Statistics & Wilson Confidence Interval Service.

Calculates descriptive statistics (mean, median, std, min, max, positive rate)
and Wilson 95% confidence intervals for benchmark-adjusted excess returns across
1D, 3D, and 5D horizons.
"""

from __future__ import annotations

import logging
import math
import statistics
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel

from backend.app.services.event_study import EventStudyResult

logger = logging.getLogger(__name__)


class EventStatisticsResult(BaseModel):
    """
    Summary statistics and confidence bounds for excess returns at a single horizon.
    """

    horizon: str
    sample_size: int = 0
    positive_count: int = 0
    negative_count: int = 0
    positive_rate: Optional[float] = None
    positive_rate_ci_lower: Optional[float] = None
    positive_rate_ci_upper: Optional[float] = None
    mean_excess_return: Optional[float] = None
    median_excess_return: Optional[float] = None
    std_excess_return: Optional[float] = None
    min_excess_return: Optional[float] = None
    max_excess_return: Optional[float] = None
    sufficient_evidence: bool = False

    model_config = {
        "extra": "forbid",
        "arbitrary_types_allowed": True,
    }


def calculate_wilson_score_interval(
    positive_count: int,
    sample_size: int,
    confidence_level: float = 0.95,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculate Wilson Score 95% Confidence Interval for a proportion.

    Parameters
    ----------
    positive_count : int
        Number of positive outcomes (k).
    sample_size : int
        Total valid sample size (n).
    confidence_level : float
        Confidence level (default 0.95, z ≈ 1.959964).

    Returns
    -------
    Tuple[Optional[float], Optional[float]]
        (lower_bound, upper_bound) rounded to 6 decimal places.
    """
    if sample_size <= 0:
        return None, None

    z = 1.959963984540054  # 95% two-sided z-score

    p_hat = positive_count / sample_size
    denom = 1.0 + (z ** 2) / sample_size
    center = (p_hat + (z ** 2) / (2.0 * sample_size)) / denom
    var_term = (p_hat * (1.0 - p_hat)) / sample_size + (z ** 2) / (4.0 * (sample_size ** 2))
    margin = (z * math.sqrt(max(0.0, var_term))) / denom

    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)

    return round(lower, 6), round(upper, 6)


def calculate_horizon_statistics(
    returns: List[float],
    horizon: str,
    min_sample_size: int = 30,
) -> EventStatisticsResult:
    """
    Calculate excess return statistics and Wilson CI for a single horizon.
    """
    valid_returns = [r for r in returns if r is not None and isinstance(r, (int, float))]
    n = len(valid_returns)

    if n == 0:
        return EventStatisticsResult(
            horizon=horizon,
            sample_size=0,
            positive_count=0,
            negative_count=0,
            positive_rate=None,
            positive_rate_ci_lower=None,
            positive_rate_ci_upper=None,
            mean_excess_return=None,
            median_excess_return=None,
            std_excess_return=None,
            min_excess_return=None,
            max_excess_return=None,
            sufficient_evidence=False,
        )

    pos_count = sum(1 for r in valid_returns if r > 0.0)
    neg_count = sum(1 for r in valid_returns if r < 0.0)
    pos_rate = round(pos_count / n, 6)

    ci_lower, ci_upper = calculate_wilson_score_interval(pos_count, n)

    mean_val = round(statistics.mean(valid_returns), 6)
    median_val = round(statistics.median(valid_returns), 6)
    min_val = round(min(valid_returns), 6)
    max_val = round(max(valid_returns), 6)

    if n >= 2:
        std_val = round(statistics.stdev(valid_returns), 6)
    else:
        std_val = 0.0

    return EventStatisticsResult(
        horizon=horizon,
        sample_size=n,
        positive_count=pos_count,
        negative_count=neg_count,
        positive_rate=pos_rate,
        positive_rate_ci_lower=ci_lower,
        positive_rate_ci_upper=ci_upper,
        mean_excess_return=mean_val,
        median_excess_return=median_val,
        std_excess_return=std_val,
        min_excess_return=min_val,
        max_excess_return=max_val,
        sufficient_evidence=(n >= min_sample_size),
    )


def _extract_excess_return(item: Any, horizon: str) -> Optional[float]:
    """Helper to extract excess return for a given horizon from various item types."""
    field_map = {
        "1D": "excess_return_1d",
        "3D": "excess_return_3d",
        "5D": "excess_return_5d",
    }
    field_name = field_map.get(horizon)
    if not field_name:
        return None

    # Check if item is EventStudyResult or has excess_return attribute directly
    if hasattr(item, field_name):
        val = getattr(item, field_name)
        if val is not None:
            return float(val)

    # Check if item is HistoricalEventFeatures or object with event_study attribute
    if hasattr(item, "event_study") and item.event_study is not None:
        es = item.event_study
        if hasattr(es, field_name):
            val = getattr(es, field_name)
            if val is not None:
                return float(val)

    # Check dict
    if isinstance(item, dict):
        if field_name in item and item[field_name] is not None:
            return float(item[field_name])
        es = item.get("event_study")
        if isinstance(es, dict) and field_name in es and es[field_name] is not None:
            return float(es[field_name])
        if hasattr(es, field_name):
            val = getattr(es, field_name)
            if val is not None:
                return float(val)

    return None


def calculate_event_statistics(
    event_studies: List[Union[EventStudyResult, Any]],
    min_sample_size: int = 30,
) -> Dict[str, EventStatisticsResult]:
    """
    Calculate 1D, 3D, and 5D event statistics across a collection of event study results.

    Parameters
    ----------
    event_studies : List[Union[EventStudyResult, Any]]
        List of EventStudyResult or HistoricalEventFeatures objects.
    min_sample_size : int
        Minimum sample size required for sufficient evidence flag.

    Returns
    -------
    Dict[str, EventStatisticsResult]
        Dictionary with keys "1D", "3D", "5D".
    """
    horizons = ["1D", "3D", "5D"]
    results: Dict[str, EventStatisticsResult] = {}

    for h in horizons:
        returns = []
        for item in event_studies or []:
            val = _extract_excess_return(item, h)
            if val is not None:
                returns.append(val)
        results[h] = calculate_horizon_statistics(returns, horizon=h, min_sample_size=min_sample_size)

    return results
