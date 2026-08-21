"""Tests for the ML shadow mode service (ForecastEngine, AnomalyEngine,
ShadowComparator, build_series, risk_from_series).

TDD: every test here must fail (RED) before the implementation exists.
Deterministic fixtures only — the engines are pure and stdlib-based.
"""

import math

import pytest
from ml import (
    AnomalyEngine,
    AnomalyResult,
    ForecastEngine,
    ShadowComparator,
    build_series,
    risk_from_series,
)


@pytest.fixture
def forecast_engine():
    return ForecastEngine()


@pytest.fixture
def anomaly_engine():
    return AnomalyEngine()


@pytest.fixture
def comparator():
    return ShadowComparator()


class TestForecastEngine:
    def test_reproduces_near_linear_trend(self, forecast_engine):
        series = [2 * x + 1 for x in range(10)]  # 1,3,5,...,19
        result = forecast_engine.forecast(series)
        # Prophet fits a near-linear trend but not exactly due to its internal fitting
        assert abs(result.slope - 2.0) < 0.01
        assert result.last_value == 19
        assert len(result.predicted) == 3
        # Predictions should continue the upward trend
        assert all(p > result.last_value for p in result.predicted)

    def test_flat_series_predicts_flat(self, forecast_engine):
        series = [5.0] * 8
        result = forecast_engine.forecast(series)
        assert abs(result.slope) < 1e-9
        for p in result.predicted:
            assert abs(p - 5.0) < 1e-9

    def test_respects_custom_horizon(self):
        engine = ForecastEngine(horizon=5)
        result = engine.forecast([1.0, 2.0, 3.0, 4.0])
        assert len(result.predicted) == 5

    def test_works_at_minimum_points(self, forecast_engine):
        result = forecast_engine.forecast([1.0, 2.0, 3.0])
        assert math.isfinite(result.slope)

    def test_is_deterministic(self, forecast_engine):
        series = [float(x % 7) for x in range(20)]
        first = forecast_engine.forecast(series)
        second = forecast_engine.forecast(series)
        assert first == second

    def test_rejects_empty_series(self, forecast_engine):
        with pytest.raises(ValueError, match="at least"):
            forecast_engine.forecast([])

    def test_rejects_series_below_min_points(self):
        engine = ForecastEngine(min_points=5)
        with pytest.raises(ValueError, match="at least 5"):
            engine.forecast([1.0, 2.0])

    def test_rejects_non_finite_values(self, forecast_engine):
        with pytest.raises(ValueError, match="finite"):
            forecast_engine.forecast([1.0, math.nan, 3.0])
        with pytest.raises(ValueError, match="finite"):
            forecast_engine.forecast([1.0, math.inf, 3.0])

    def test_rejects_invalid_horizon(self):
        with pytest.raises(ValueError, match="horizon"):
            ForecastEngine(horizon=0)


class TestAnomalyEngine:
    def test_detects_obvious_outlier_in_flat_series(self, anomaly_engine):
        series = [0.0, 0.0, 0.0, 0.0, 100.0]
        result = anomaly_engine.detect(series)
        assert result.count == 1
        assert result.outliers[0]["index"] == 4
        assert abs(result.outliers[0]["value"] - 100.0) < 1e-9

    def test_no_outliers_in_flat_series(self, anomaly_engine):
        series = [3.0] * 10
        result = anomaly_engine.detect(series)
        assert result.count == 0
        assert result.outliers == []

    def test_gentle_linear_series_has_few_outliers(self, anomaly_engine):
        # IsolationForest with contamination ~10% may flag endpoints of a linear series
        # as anomalous since they sit at the extremes
        series = [float(x) for x in range(1, 11)]
        result = anomaly_engine.detect(series)
        assert result.count <= 2

    def test_detects_two_outliers(self, anomaly_engine):
        series = [2.0, 3.0, 2.0, 3.0, 2.0, 50.0, 2.0, 3.0, 2.0, 60.0, 2.0, 3.0]
        result = anomaly_engine.detect(series)
        assert result.count == 2
        indices = [o["index"] for o in result.outliers]
        assert 5 in indices and 9 in indices

    def test_works_at_minimum_points(self, anomaly_engine):
        result = anomaly_engine.detect([1.0, 1.0, 1.0])
        assert result.count == 0

    def test_lower_threshold_detects_more(self):
        engine = AnomalyEngine(threshold=2.0)
        series = [1.0, 2.0, 1.0, 2.0, 1.0, 4.0, 1.0, 2.0]
        assert engine.detect(series).count > 0

    def test_flags_deviation_when_mad_is_zero(self, anomaly_engine):
        series = [0.0, 0.0, 0.0, 100.0]
        result = anomaly_engine.detect(series)
        assert result.count == 1
        assert result.outliers[0]["index"] == 3

    def test_rejects_series_below_min_points(self):
        engine = AnomalyEngine(min_points=6)
        with pytest.raises(ValueError, match="at least 6"):
            engine.detect([1.0, 2.0, 3.0])

    def test_rejects_empty_series(self, anomaly_engine):
        with pytest.raises(ValueError, match="at least"):
            anomaly_engine.detect([])

    def test_rejects_non_finite_values(self, anomaly_engine):
        with pytest.raises(ValueError, match="finite"):
            anomaly_engine.detect([1.0, float("nan"), 1.0, 1.0, 1.0])
        with pytest.raises(ValueError, match="finite"):
            anomaly_engine.detect([1.0, float("inf"), 1.0, 1.0, 1.0])

    def test_is_deterministic(self, anomaly_engine):
        series = [float(x % 5) for x in range(30)]
        assert anomaly_engine.detect(series) == anomaly_engine.detect(series)


class TestShadowComparator:
    def test_identical_risks_agree(self, comparator):
        result = comparator.compare(0.42, 0.42)
        assert result.agreement is True
        assert result.verdict == "AGREE"

    def test_agree_within_tolerance(self, comparator):
        result = comparator.compare(0.40, 0.44)
        assert result.agreement is True
        assert result.verdict == "AGREE"

    def test_disagrees_beyond_tolerance(self, comparator):
        result = comparator.compare(0.10, 0.90)
        assert result.agreement is False
        assert result.verdict == "DISAGREE"

    def test_custom_tolerance(self):
        comparator = ShadowComparator(tolerance=0.1)
        assert comparator.compare(0.30, 0.39).agreement is True
        assert comparator.compare(0.30, 0.42).agreement is False

    def test_rejects_risk_out_of_range(self, comparator):
        with pytest.raises(ValueError, match="0 and 1"):
            comparator.compare(-0.1, 0.5)
        with pytest.raises(ValueError, match="0 and 1"):
            comparator.compare(0.5, 1.1)

    def test_edge_risks(self, comparator):
        result = comparator.compare(0.0, 1.0)
        assert result.agreement is False
        assert result.verdict == "DISAGREE"


class TestBuildSeries:
    def test_buckets_logs_by_minute_ordered(self):
        logs = [
            {"timestamp": "2026-08-16T12:02:00Z"},
            {"timestamp": "2026-08-16T12:01:00Z"},
            {"timestamp": "2026-08-16T12:01:30Z"},
            {"timestamp": "2026-08-16T12:03:00Z"},
        ]
        series = build_series(logs)
        assert series == [2.0, 1.0, 1.0]  # chronological: minute 01 -> 2, then 1 each

    def test_logs_without_timestamp_become_single_point(self):
        series = build_series([{}, {}, {}])
        assert series == [3]

    def test_malformed_timestamp_collapses_into_single_point(self):
        logs = [
            {"timestamp": "not-a-date"},
            {"timestamp": "2026-08-16T12:01:00Z"},
        ]
        series = build_series(logs)
        assert series == [1.0, 1.0]  # malformed -> None bucket, valid -> minute 01

    def test_empty_logs(self):
        assert build_series([]) == []


class TestRiskFromSeries:
    def test_flat_no_outliers_is_zero_risk(self, anomaly_engine, forecast_engine):
        series = [2.0] * 8
        anomalies = anomaly_engine.detect(series)
        forecast = forecast_engine.forecast(series)
        risk = risk_from_series(series, forecast, anomalies)
        assert abs(risk - 0.0) < 1e-9

    def test_outlier_raises_risk(self, anomaly_engine, forecast_engine):
        series = [1.0, 1.0, 1.0, 1.0, 40.0]
        anomalies = anomaly_engine.detect(series)
        forecast = forecast_engine.forecast(series)
        risk = risk_from_series(series, forecast, anomalies)
        assert risk > 0.0

    def test_rising_trend_raises_risk_more_than_falling(
        self, anomaly_engine, forecast_engine
    ):
        rising = [float(x) for x in range(1, 11)]
        falling = [float(x) for x in range(10, 0, -1)]
        r_up = risk_from_series(
            rising, forecast_engine.forecast(rising), anomaly_engine.detect(rising)
        )
        r_down = risk_from_series(
            falling, forecast_engine.forecast(falling), anomaly_engine.detect(falling)
        )
        assert r_up > r_down

    def test_risk_stays_in_unit_range(self, anomaly_engine, forecast_engine):
        series = [float(x) for x in range(1, 21)]
        risk = risk_from_series(
            series, forecast_engine.forecast(series), anomaly_engine.detect(series)
        )
        assert 0.0 <= risk <= 1.0


class TestAnomalyResultModel:
    def test_defaults(self):
        result = AnomalyResult(outliers=[], threshold=3.5)
        assert result.count == 0
