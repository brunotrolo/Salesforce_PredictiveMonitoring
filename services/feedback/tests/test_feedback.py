"""Contratos e bordas dos engines de feedback loop (Phase 4).

Cobertura exigida: 100% de services/feedback (spec
docs/FEEDBACK_LOOP_SPEC.md).
"""

import json
from pathlib import Path

import pytest
from feedback import (
    AccuracyTracker,
    Calibrator,
    FeedbackRecord,
    FeedbackStore,
    SampleStore,
    accuracy_direction,
)
from feedback.calibrate import main as calibrate_main

# ---------------------------------------------------------------- AccuracyTracker


class TestAccuracyTracker:
    def test_no_data_when_prev_has_no_shadow_mode(self):
        result = AccuracyTracker().evaluate({"risk_score": 0.1}, {"series": [1.0, 2.0]})
        assert result.status == "no_data"

    def test_no_data_when_prev_shadow_disabled(self):
        prev = {"shadow_mode": {"enabled": False, "reason": "x"}}
        result = AccuracyTracker().evaluate(prev, {"series": [1.0, 2.0]})
        assert result.status == "no_data"

    def test_no_data_when_prev_missing_forecast_or_anomalies(self):
        prev = {"shadow_mode": {"enabled": True, "series": [0.0, 1.0]}}
        result = AccuracyTracker().evaluate(prev, {"series": [1.0, 2.0]})
        assert result.status == "no_data"

    def test_no_data_when_current_has_no_series(self):
        prev = {
            "shadow_mode": {
                "enabled": True,
                "forecast": {"slope": 1.0},
                "anomalies": {"count": 0},
                "series": [0.0, 1.0],
            }
        }
        result = AccuracyTracker().evaluate(prev, {"risk_score": 0.5})
        assert result.status == "no_data"

    def test_no_data_when_current_series_too_short(self, prev_snapshot_with_shadow):
        current = {"shadow_mode": {"series": [1.0]}}
        result = AccuracyTracker().evaluate(prev_snapshot_with_shadow, current)
        assert result.status == "no_data"

    def test_hit_when_expected_up_and_actual_up(
        self, prev_snapshot_with_shadow, current_snapshot_series_up
    ):
        result = AccuracyTracker().evaluate(
            prev_snapshot_with_shadow, current_snapshot_series_up
        )
        assert result.status == "evaluated"
        assert result.direction_expected == "up"
        assert result.direction_actual == "up"
        assert result.forecast_hit is True
        assert result.anomaly_flagged is True
        assert result.anomaly_hit is True
        assert result.false_positive is False
        assert result.series_actual == [2.0, 4.0, 6.0, 8.0, 10.0, 12.0]

    def test_miss_when_expected_up_and_actual_flat(
        self, prev_snapshot_with_shadow, current_snapshot_series_flat
    ):
        result = AccuracyTracker().evaluate(
            prev_snapshot_with_shadow, current_snapshot_series_flat
        )
        assert result.status == "evaluated"
        assert result.direction_expected == "up"
        assert result.direction_actual == "flat"
        assert result.forecast_hit is False
        assert result.anomaly_hit is False
        assert result.false_positive is True

    def test_flat_expected_is_indeterminate(self, current_snapshot_series_up):
        prev = {
            "shadow_mode": {
                "enabled": True,
                "forecast": {"slope": 0.0},
                "anomalies": {"count": 0},
                "series": [1.0, 1.0, 1.0],
            }
        }
        result = AccuracyTracker().evaluate(prev, current_snapshot_series_up)
        assert result.status == "evaluated"
        assert result.direction_expected == "flat"
        assert result.forecast_hit is None

    def test_down_direction_detected(self, current_snapshot_series_flat):
        prev = {
            "shadow_mode": {
                "enabled": True,
                "forecast": {"slope": -1.5},
                "anomalies": {"count": 0},
                "series": [10.0, 10.0, 10.0],
            }
        }
        result = AccuracyTracker().evaluate(prev, current_snapshot_series_flat)
        assert result.direction_expected == "down"
        assert result.direction_actual == "flat"
        assert result.forecast_hit is False

    def test_anomaly_not_flagged(self, current_snapshot_series_up):
        prev = {
            "shadow_mode": {
                "enabled": True,
                "forecast": {"slope": 1.0},
                "anomalies": {"count": 0},
                "series": [0.0, 1.0, 2.0],
            }
        }
        result = AccuracyTracker().evaluate(prev, current_snapshot_series_up)
        assert result.anomaly_flagged is False
        assert result.anomaly_hit is None
        assert result.false_positive is False

    def test_raises_on_non_finite_values(self, prev_snapshot_with_shadow):
        with pytest.raises(ValueError, match="finite"):
            AccuracyTracker().evaluate(
                prev_snapshot_with_shadow,
                {"shadow_mode": {"series": [1.0, float("nan")]}},
            )

    def test_raises_on_non_finite_prev_series(self):
        prev = {
            "shadow_mode": {
                "enabled": True,
                "forecast": {"slope": 1.0},
                "anomalies": {"count": 0},
                "series": [0.0, float("inf")],
            }
        }
        with pytest.raises(ValueError, match="finite"):
            AccuracyTracker().evaluate(prev, {"shadow_mode": {"series": [1.0, 2.0]}})

    def test_median_even_length_series(self):
        """Median of an even-length series: anomalies flagged against a
        4-point baseline must not raise (covers the mid-pair branch)."""
        prev = {
            "shadow_mode": {
                "enabled": True,
                "forecast": {"slope": 1.0},
                "anomalies": {"count": 1},
                "series": [10.0, 20.0, 30.0, 40.0],
            }
        }
        current = {"shadow_mode": {"series": [45.0, 46.0, 47.0, 48.0]}}
        result = AccuracyTracker().evaluate(prev, current)
        assert result.status == "evaluated"
        assert result.anomaly_hit is True


class TestAccuracyDirection:
    def test_returns_expected(self):
        assert accuracy_direction(2.0) == "up"
        assert accuracy_direction(-0.5) == "down"
        assert accuracy_direction(0.0) == "flat"


# ------------------------------------------------------------------ FeedbackStore


class TestFeedbackStore:
    def test_load_valid_file(self, tmp_path: Path):
        path = tmp_path / "feedback.json"
        path.write_text(
            json.dumps(
                [
                    {"id": "a1", "target": "anomaly", "action": "true_positive"},
                    {"id": "a2", "target": "anomaly", "action": "false_positive"},
                    {"id": "b1", "target": "alert", "action": "true_positive"},
                ]
            )
        )
        result = FeedbackStore().load(path)
        assert result.loaded == 3
        assert result.valid == 3
        assert result.invalid == 0
        assert result.by_action == {
            "true_positive": 2,
            "false_positive": 1,
        }
        assert result.by_target == {"anomaly": 2, "alert": 1}
        assert isinstance(result.records[0], FeedbackRecord)

    def test_ignores_invalid_rows(self, tmp_path: Path):
        path = tmp_path / "feedback.json"
        path.write_text(
            json.dumps(
                [
                    {"id": "ok", "target": "alert", "action": "false_positive"},
                    {"id": 42, "target": "alert", "action": "false_positive"},
                    {"id": "bad-action", "target": "alert", "action": "maybe"},
                    {"id": "bad-target", "target": "widget", "action": "true_positive"},
                    {"id": "missing-fields"},
                    "not-a-dict",
                ]
            )
        )
        result = FeedbackStore().load(path)
        assert result.loaded == 6
        assert result.valid == 1
        assert result.invalid == 5
        assert result.by_action == {"false_positive": 1}

    def test_load_empty_list(self, tmp_path: Path):
        path = tmp_path / "feedback.json"
        path.write_text("[]")
        result = FeedbackStore().load(path)
        assert result.loaded == 0
        assert result.valid == 0
        assert result.invalid == 0

    def test_raises_on_missing_file(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match="feedback.json"):
            FeedbackStore().load(tmp_path / "feedback.json")

    def test_raises_on_non_list_root(self, tmp_path: Path):
        path = tmp_path / "feedback.json"
        path.write_text('{"id": "a"}')
        with pytest.raises(ValueError, match="list"):
            FeedbackStore().load(path)

    def test_raises_on_invalid_json(self, tmp_path: Path):
        path = tmp_path / "feedback.json"
        path.write_text("{not json")
        with pytest.raises(ValueError, match="JSON"):
            FeedbackStore().load(path)

    def test_note_and_timestamp_preserved(self, tmp_path: Path):
        path = tmp_path / "feedback.json"
        path.write_text(
            json.dumps(
                [
                    {
                        "id": "a1",
                        "target": "anomaly",
                        "action": "false_positive",
                        "timestamp": "2026-08-16T12:00:00Z",
                        "note": "era manutenção programada",
                    }
                ]
            )
        )
        result = FeedbackStore().load(path)
        assert result.records[0].note == "era manutenção programada"
        assert result.records[0].timestamp == "2026-08-16T12:00:00Z"


# --------------------------------------------------------------------- Calibrator


class TestCalibrator:
    def test_insufficient_samples(self):
        result = Calibrator().recommend([{"threshold": 3.5, "fp_rate": 0.3}])
        assert result.status == "insufficient"
        assert result.samples == 1
        assert result.recommended_threshold is None

    def test_insufficient_when_empty(self):
        result = Calibrator().recommend([])
        assert result.status == "insufficient"
        assert result.samples == 0

    def test_raises_threshold_up_when_fp_above_target(self):
        samples = [
            {"threshold": 3.5, "fp_rate": 0.5},
            {"threshold": 3.5, "fp_rate": 0.4},
            {"threshold": 3.5, "fp_rate": 0.6},
        ]
        result = Calibrator().recommend(samples)
        assert result.status == "recommended"
        assert result.avg_fp_rate == pytest.approx(0.5)
        assert result.current_threshold == pytest.approx(3.5)
        assert result.recommended_threshold == pytest.approx(4.0)

    def test_lowers_threshold_when_fp_below_half_target(self):
        samples = [
            {"threshold": 4.0, "fp_rate": 0.05},
            {"threshold": 4.0, "fp_rate": 0.04},
            {"threshold": 4.0, "fp_rate": 0.06},
        ]
        result = Calibrator().recommend(samples)
        assert result.recommended_threshold == pytest.approx(3.75)

    def test_keeps_threshold_when_fp_within_band(self):
        samples = [
            {"threshold": 3.5, "fp_rate": 0.15},
            {"threshold": 3.5, "fp_rate": 0.2},
            {"threshold": 3.5, "fp_rate": 0.18},
        ]
        result = Calibrator().recommend(samples)
        assert result.recommended_threshold == pytest.approx(3.5)

    def test_clamps_to_max_threshold(self):
        samples = [
            {"threshold": 5.5, "fp_rate": 0.9},
            {"threshold": 5.5, "fp_rate": 0.8},
            {"threshold": 5.5, "fp_rate": 0.85},
        ]
        result = Calibrator().recommend(samples)
        assert result.recommended_threshold == pytest.approx(6.0)

    def test_clamps_to_min_threshold(self):
        samples = [
            {"threshold": 2.2, "fp_rate": 0.01},
            {"threshold": 2.2, "fp_rate": 0.0},
            {"threshold": 2.2, "fp_rate": 0.02},
        ]
        result = Calibrator().recommend(samples)
        assert result.recommended_threshold == pytest.approx(2.0)

    def test_raises_on_fp_rate_out_of_range(self):
        with pytest.raises(ValueError, match="fp_rate"):
            Calibrator().recommend(
                [
                    {"threshold": 3.5, "fp_rate": 1.5},
                    {"threshold": 3.5, "fp_rate": 0.2},
                    {"threshold": 3.5, "fp_rate": 0.2},
                ]
            )

    def test_raises_on_non_finite_values(self):
        with pytest.raises(ValueError, match="finite"):
            Calibrator().recommend(
                [
                    {"threshold": float("nan"), "fp_rate": 0.2},
                    {"threshold": 3.5, "fp_rate": 0.2},
                    {"threshold": 3.5, "fp_rate": 0.2},
                ]
            )

    def test_deterministic(self):
        samples = [
            {"threshold": 3.5, "fp_rate": 0.4},
            {"threshold": 3.5, "fp_rate": 0.3},
            {"threshold": 3.5, "fp_rate": 0.5},
        ]
        a = Calibrator().recommend(samples)
        b = Calibrator().recommend(samples)
        assert a.model_dump() == b.model_dump()


# ------------------------------------------------------------- calibrate CLI


class TestCalibrateCLI:
    def test_recommends_and_prints_json(self, tmp_path: Path, capsys):
        path = tmp_path / "samples.json"
        path.write_text(
            json.dumps(
                [
                    {"threshold": 3.5, "fp_rate": 0.5},
                    {"threshold": 3.5, "fp_rate": 0.4},
                    {"threshold": 3.5, "fp_rate": 0.6},
                ]
            )
        )
        assert calibrate_main(["--samples", str(path), "--target", "0.2"]) == 0
        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "recommended"
        assert out["recommended_threshold"] == 4.0

    def test_insufficient_returns_nonzero(self, tmp_path: Path, capsys):
        path = tmp_path / "samples.json"
        path.write_text(json.dumps([{"threshold": 3.5, "fp_rate": 0.5}]))
        assert calibrate_main(["--samples", str(path)]) == 1
        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "insufficient"

    def test_missing_samples_file(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            calibrate_main(["--samples", str(tmp_path / "nope.json")])


# ---------------------------------------------------------------- SampleStore


class TestSampleStore:
    def test_load_missing_file_returns_empty(self, tmp_path: Path):
        assert SampleStore().load(tmp_path / "nope.json") == []

    def test_load_valid_list(self, tmp_path: Path):
        path = tmp_path / "samples.json"
        path.write_text(json.dumps([{"threshold": 3.5, "fp_rate": 0.4}]))
        assert SampleStore().load(path) == [{"threshold": 3.5, "fp_rate": 0.4}]

    def test_load_invalid_json_raises(self, tmp_path: Path):
        path = tmp_path / "samples.json"
        path.write_text("{not json")
        with pytest.raises(ValueError, match="invalid JSON"):
            SampleStore().load(path)

    def test_load_non_list_raises(self, tmp_path: Path):
        path = tmp_path / "samples.json"
        path.write_text('{"threshold": 3.5}')
        with pytest.raises(ValueError, match="must contain a JSON list"):
            SampleStore().load(path)

    def test_load_skips_non_dict_rows(self, tmp_path: Path):
        path = tmp_path / "samples.json"
        path.write_text(json.dumps([{"threshold": 3.5, "fp_rate": 0.4}, "garbage"]))
        assert SampleStore().load(path) == [{"threshold": 3.5, "fp_rate": 0.4}]

    def test_add_appends_observation(self):
        samples = [{"threshold": 3.5, "fp_rate": 0.4}]
        updated = SampleStore().add(samples, 4.0, 1.0)
        assert updated == [
            {"threshold": 3.5, "fp_rate": 0.4},
            {"threshold": 4.0, "fp_rate": 1.0},
        ]
        assert samples == [{"threshold": 3.5, "fp_rate": 0.4}]  # imutável

    def test_add_caps_rolling_window(self):
        store = SampleStore(max_samples=2)
        samples: list[dict] = []
        for i in range(4):
            samples = store.add(samples, 3.5, 0.5)
        assert samples == [
            {"threshold": 3.5, "fp_rate": 0.5},
            {"threshold": 3.5, "fp_rate": 0.5},
        ]

    def test_save_round_trip(self, tmp_path: Path):
        path = tmp_path / "samples.json"
        samples = [{"threshold": 4.0, "fp_rate": 1.0}]
        SampleStore().save(path, samples)
        assert SampleStore().load(path) == samples
