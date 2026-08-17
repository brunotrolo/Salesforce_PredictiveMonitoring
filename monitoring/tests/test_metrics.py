"""Tests for the Prometheus text exposition module (Phase 5)."""

from metrics import build_prometheus_metrics


def _snapshot(**overrides):
    base = {
        "timestamp": "2026-08-17T10:00:00+00:00",
        "mode": "mock",
        "risk_score": 0.42,
        "errors_count": 3,
        "slow_requests_count": 1,
        "retried_count": 2,
        "logs_processed": 10,
        "health_check": {"status": "HEALTHY"},
        "severity_counts": {"CRITICAL": 1, "WARNING": 2},
        "shadow_mode": {
            "enabled": True,
            "ml_risk": 0.5,
        },
        "pipeline": {
            "duration_ms": 137,
            "steps": ["collect", "analyze"],
            "step_errors": [],
        },
    }
    base.update(overrides)
    return base


class TestBuildPrometheusMetrics:
    def test_ends_with_newline(self):
        assert build_prometheus_metrics(_snapshot()).endswith("\n")

    def test_has_metadata_for_pipeline_info(self):
        text = build_prometheus_metrics(_snapshot())
        assert "# HELP monitoring_pipeline_info" in text
        assert "# TYPE monitoring_pipeline_info gauge" in text
        assert 'monitoring_pipeline_info{mode="mock",health="HEALTHY"} 1' in text

    def test_renders_core_series(self):
        text = build_prometheus_metrics(_snapshot())
        assert "# HELP monitoring_risk_score" in text
        assert "# TYPE monitoring_risk_score gauge" in text
        assert "monitoring_risk_score 0.42" in text
        assert "monitoring_errors_count 3" in text
        assert "monitoring_slow_requests_count 1" in text
        assert "monitoring_retried_count 2" in text
        assert "monitoring_logs_processed 10" in text

    def test_pipeline_block_metrics(self):
        text = build_prometheus_metrics(_snapshot())
        assert "monitoring_pipeline_duration_ms 137" in text
        assert "monitoring_pipeline_step_errors_count 0" in text

    def test_step_errors_count_reflects_errors(self):
        snap = _snapshot(pipeline={"duration_ms": 50, "step_errors": [{"step": "x"}]})
        text = build_prometheus_metrics(snap)
        assert "monitoring_pipeline_step_errors_count 1" in text

    def test_alerts_by_severity(self):
        text = build_prometheus_metrics(_snapshot())
        assert "# HELP monitoring_alerts_total" in text
        assert 'monitoring_alerts_total{severity="CRITICAL"} 1' in text
        assert 'monitoring_alerts_total{severity="WARNING"} 2' in text

    def test_alerts_omitted_when_no_severity_counts(self):
        text = build_prometheus_metrics(_snapshot(severity_counts={}))
        assert "monitoring_alerts_total" not in text

    def test_shadow_metrics_when_enabled(self):
        text = build_prometheus_metrics(_snapshot())
        assert "# HELP monitoring_shadow_ml_risk" in text
        assert "monitoring_shadow_ml_risk 0.5" in text

    def test_shadow_metrics_omitted_when_disabled(self):
        text = build_prometheus_metrics(_snapshot(shadow_mode={"enabled": False}))
        assert "monitoring_shadow_ml_risk" not in text

    def test_timestamp_iso_with_offset(self):
        text = build_prometheus_metrics(_snapshot())
        assert "monitoring_cycle_timestamp_seconds 1.78696e+09" in text

    def test_timestamp_iso_with_z_suffix(self):
        text = build_prometheus_metrics(_snapshot(timestamp="2026-08-17T10:00:00Z"))
        assert "monitoring_cycle_timestamp_seconds 1.78696e+09" in text

    def test_timestamp_missing_defaults_to_zero(self):
        text = build_prometheus_metrics(_snapshot(timestamp=""))
        assert "monitoring_cycle_timestamp_seconds 0" in text

    def test_timestamp_garbage_defaults_to_zero(self):
        text = build_prometheus_metrics(_snapshot(timestamp="not-a-date"))
        assert "monitoring_cycle_timestamp_seconds 0" in text

    def test_missing_fields_default_to_zero(self):
        text = build_prometheus_metrics(
            _snapshot(
                risk_score=None,
                errors_count="x",
                slow_requests_count=True,
                retried_count=None,
                logs_processed=None,
                pipeline=None,
                health_check=None,
            )
        )
        assert "monitoring_risk_score 0" in text
        assert "monitoring_errors_count 0" in text
        assert "monitoring_slow_requests_count 0" in text
        assert "monitoring_retried_count 0" in text
        assert "monitoring_logs_processed 0" in text
        assert "monitoring_pipeline_duration_ms 0" in text
        assert "monitoring_pipeline_step_errors_count 0" in text
        assert 'monitoring_pipeline_info{mode="mock",health="UNKNOWN"} 1' in text

    def test_sanitizes_mode_and_health_labels(self):
        snap = _snapshot(mode="real prod!", health_check={"status": "WARN ING"})
        text = build_prometheus_metrics(snap)
        assert 'monitoring_pipeline_info{mode="real_prod_",health="WARN_ING"} 1' in text

    def test_parses_line_by_line(self):
        text = build_prometheus_metrics(_snapshot())
        for line in text.splitlines():
            assert line.startswith("#") or " " in line
