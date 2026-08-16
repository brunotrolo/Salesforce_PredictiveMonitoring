"""Tests for the monitoring pipeline orchestrator (mock mode)."""

import json
import sys

import orchestrate


class TestRunPipeline:
    def test_returns_all_expected_keys(self):
        result, _ = orchestrate.run_pipeline()
        expected_keys = {
            "timestamp",
            "risk_score",
            "errors_count",
            "slow_requests_count",
            "alerts",
            "comparison",
            "health_check",
            "validation",
            "logs_processed",
        }
        assert expected_keys.issubset(result.keys())

    def test_processes_all_mock_logs(self):
        result, raw_logs = orchestrate.run_pipeline()
        assert result["logs_processed"] == 3
        assert len(raw_logs) == 3

    def test_risk_score_is_between_zero_and_one(self):
        result, _ = orchestrate.run_pipeline()
        assert 0 <= result["risk_score"] <= 1

    def test_detects_critical_error_alert(self):
        result, _ = orchestrate.run_pipeline()
        critical = [a for a in result["alerts"] if a["severity"] == "CRITICAL"]
        assert len(critical) == 1
        assert "status 500" in critical[0]["message"]

    def test_detects_slow_request_alert(self):
        result, _ = orchestrate.run_pipeline()
        warnings = [a for a in result["alerts"] if a["severity"] == "WARNING"]
        assert len(warnings) == 1
        assert "1500ms" in warnings[0]["message"]

    def test_health_check_is_valid(self):
        result, _ = orchestrate.run_pipeline()
        assert result["health_check"]["status"] in ("HEALTHY", "WARNING")
        assert result["health_check"]["last_updated"]

    def test_comparison_has_all_fields(self):
        result, _ = orchestrate.run_pipeline()
        comparison = result["comparison"]
        assert comparison["prediction"] in (
            "CRITICAL_INCREASE",
            "MODERATE_INCREASE",
            "IMPROVEMENT",
            "STABLE",
        )
        assert 0 <= comparison["confidence"] <= 1
        assert isinstance(comparison["risk_delta"], (int, float))
        assert comparison["summary"]

    def test_validation_passes_for_mock_data(self):
        result, _ = orchestrate.run_pipeline()
        assert result["validation"]["valid"] is True
        assert result["validation"]["errors"] == []


class TestMain:
    def test_writes_json_output_file(self, tmp_path, monkeypatch):
        output = tmp_path / "output.json"
        monkeypatch.setattr(sys, "argv", ["orchestrate.py", "--log-file", str(output)])
        orchestrate.main()
        assert output.exists()
        data = json.loads(output.read_text())
        assert "risk_score" in data
        assert "health_check" in data

    def test_invalid_mode_exits_with_error(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["orchestrate.py", "--mode", "real"])
        try:
            orchestrate.main()
            raise AssertionError("expected SystemExit")
        except SystemExit as e:
            assert e.code == 2

    def test_raises_when_pipeline_result_missing_keys(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            orchestrate, "run_pipeline", lambda: ({"risk_score": 0.5}, [])
        )
        output = tmp_path / "output.json"
        monkeypatch.setattr(sys, "argv", ["orchestrate.py", "--log-file", str(output)])
        try:
            orchestrate.main()
            raise AssertionError("expected ValueError")
        except ValueError as e:
            assert "missing required keys" in str(e)

    def test_raises_when_risk_score_out_of_range(self, tmp_path, monkeypatch):
        bad_result = {"risk_score": 1.5, "alerts": [], "health_check": {}}
        monkeypatch.setattr(orchestrate, "run_pipeline", lambda: (bad_result, []))
        output = tmp_path / "output.json"
        monkeypatch.setattr(sys, "argv", ["orchestrate.py", "--log-file", str(output)])
        try:
            orchestrate.main()
            raise AssertionError("expected ValueError")
        except ValueError as e:
            assert "out of range" in str(e)
