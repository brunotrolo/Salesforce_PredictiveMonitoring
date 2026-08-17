"""ML shadow mode engines (Phase 3).

Deterministic, stdlib-only implementations so the pipeline can compare
heuristic vs ML risk without adding heavy ML dependencies. The engines
expose small interfaces so a real Prophet / sklearn IsolationForest can
replace the internals later without touching the pipeline (see
docs/ML_SHADOW_MODE_SPEC.md).
"""

from __future__ import annotations

import math
from datetime import datetime

from pydantic import BaseModel


class ForecastResult(BaseModel):
    slope: float
    intercept: float
    predicted: list[float]
    last_value: float


class AnomalyResult(BaseModel):
    outliers: list[dict]
    threshold: float
    count: int = 0


class ShadowComparison(BaseModel):
    heuristic_risk: float
    ml_risk: float
    agreement: bool
    verdict: str


class ForecastEngine:
    """Least-squares linear fit projecting the next ``horizon`` points."""

    def __init__(self, horizon: int = 3, min_points: int = 3) -> None:
        if horizon < 1:
            raise ValueError("horizon must be >= 1")
        self.horizon = horizon
        self.min_points = min_points

    def forecast(self, series: list[float]) -> ForecastResult:
        if len(series) < self.min_points:
            raise ValueError(f"series must have at least {self.min_points} points")
        if not all(math.isfinite(float(v)) for v in series):
            raise ValueError("series must contain only finite values")
        xs = list(range(len(series)))
        slope, intercept = _least_squares(xs, [float(v) for v in series])
        next_x = len(series)
        predicted = [intercept + slope * (next_x + i) for i in range(self.horizon)]
        return ForecastResult(
            slope=slope,
            intercept=intercept,
            predicted=predicted,
            last_value=float(series[-1]),
        )


class AnomalyEngine:
    """Robust anomaly detection via modified z-score (median + MAD).

    When MAD is ~0 (degenerate series: no spread around the median, e.g.
    error counts where most minutes are 0) any point deviating from the
    median is flagged — a lone spike in a sea of zeros is exactly the
    anomaly monitoring cares about.
    """

    def __init__(self, threshold: float = 3.5, min_points: int = 3) -> None:
        self.threshold = threshold
        self.min_points = min_points

    def detect(self, series: list[float]) -> AnomalyResult:
        if len(series) < self.min_points:
            raise ValueError(f"series must have at least {self.min_points} points")
        values = [float(v) for v in series]
        if not all(math.isfinite(v) for v in values):
            raise ValueError("series must contain only finite values")

        median = _median(values)
        deviations = [abs(v - median) for v in values]
        mad = _median(deviations)

        outliers: list[dict] = []
        scale = 0.6745 / mad if mad > 1e-12 else None
        for i, v in enumerate(values):
            if scale is None:
                flagged = v != median
            else:
                flagged = abs(scale * (v - median)) > self.threshold
            if flagged:
                z = scale * (v - median) if scale is not None else None
                outliers.append({"index": i, "value": v, "z_score": z})
        return AnomalyResult(
            outliers=outliers, threshold=self.threshold, count=len(outliers)
        )


class ShadowComparator:
    """Side-by-side heuristic vs ML risk (shadow mode never decides)."""

    def __init__(self, tolerance: float = 0.05) -> None:
        self.tolerance = tolerance

    def compare(self, heuristic_risk: float, ml_risk: float) -> ShadowComparison:
        for label, risk in (("heuristic", heuristic_risk), ("ml", ml_risk)):
            if not 0.0 <= risk <= 1.0:
                raise ValueError(f"{label} risk must be between 0 and 1")
        agreement = abs(heuristic_risk - ml_risk) <= self.tolerance
        return ShadowComparison(
            heuristic_risk=heuristic_risk,
            ml_risk=ml_risk,
            agreement=agreement,
            verdict="AGREE" if agreement else "DISAGREE",
        )


def build_series(logs: list[dict]) -> list[float]:
    """Bucket logs by minute (from ISO timestamps), ordered by time.

    Logs without a parseable timestamp collapse into a single point with
    the total count.
    """
    buckets: dict[tuple, int] = {}
    for log in logs:
        ts = log.get("timestamp")
        key = None
        if ts:
            try:
                dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                key = (dt.year, dt.month, dt.day, dt.hour, dt.minute)
            except ValueError:
                key = None
        buckets[key] = buckets.get(key, 0) + 1
    if not buckets:
        return []
    return [float(buckets[k]) for k in sorted(buckets, key=lambda k: (k is None, k))]


def risk_from_series(
    series: list[float],
    forecast: ForecastResult,
    anomalies: AnomalyResult,
) -> float:
    """Derive a unit-interval ML risk from outlier ratio and trend.

    Outlier share and rising trend each contribute half. A falling slope
    contributes zero trend risk.
    """
    outlier_ratio = min(1.0, anomalies.count / max(1, len(series)))
    span = max(abs(v) for v in series) if series else 0.0
    trend_ratio = 0.0
    if forecast.slope > 0 and span > 1e-9:
        trend_ratio = min(1.0, forecast.slope * len(series) / span)
    return min(1.0, max(0.0, 0.5 * outlier_ratio + 0.5 * trend_ratio))


def _least_squares(xs: list[int], ys: list[float]) -> tuple[float, float]:
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den = sum((x - mean_x) ** 2 for x in xs)
    slope = num / den if den else 0.0
    intercept = mean_y - slope * mean_x
    return slope, intercept


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0
