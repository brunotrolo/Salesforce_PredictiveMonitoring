"""ML shadow mode engines.

Scikit-learn IsolationForest for anomaly detection and Facebook Prophet for
forecasting, replacing the original stdlib-only implementations.  The public
interfaces are unchanged so the pipeline needs no modifications.

see docs/ML_SHADOW_MODE_SPEC.md
"""

from __future__ import annotations

import math
from datetime import datetime

import numpy as np
import pandas as pd
from prophet import Prophet
from pydantic import BaseModel
from sklearn.ensemble import IsolationForest


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
    """Prophet-based forecasting projecting the next ``horizon`` points."""

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

        dates = pd.date_range("2026-01-01", periods=len(series), freq="min")
        df = pd.DataFrame({"ds": dates, "y": [float(v) for v in series]})

        m = Prophet(
            yearly_seasonality=False,
            weekly_seasonality=False,
            daily_seasonality=False,
            interval_width=0.95,
        )
        m.fit(df)

        future = m.make_future_dataframe(periods=self.horizon, freq="min")
        pred = m.predict(future)
        predicted = pred["yhat"].tail(self.horizon).tolist()

        slope = (predicted[-1] - float(series[-1])) / self.horizon
        intercept = float(series[-1])

        return ForecastResult(
            slope=slope,
            intercept=intercept,
            predicted=predicted,
            last_value=float(series[-1]),
        )


class AnomalyEngine:
    """IsolationForest-based anomaly detection.

    Uses sklearn's IsolationForest with a contamination factor derived from
    the threshold parameter.  A higher threshold means fewer outliers are
    expected (lower contamination).
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

        arr = np.array(values).reshape(-1, 1)

        contamination = min(0.5, 1.0 / (self.threshold + 1))
        clf = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100,
        )
        labels = clf.fit_predict(arr)

        outliers: list[dict] = []
        for i, v in enumerate(values):
            if labels[i] == -1:
                score = float(clf.decision_function(arr[i : i + 1])[0])
                outliers.append({"index": i, "value": v, "anomaly_score": -score})

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
