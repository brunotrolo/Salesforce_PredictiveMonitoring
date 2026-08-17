"""Tests for the monitoring pipeline orchestrator (mock mode)."""

import json
import sys
from datetime import datetime, timezone

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
            "alerts_aggregated",
            "severity_counts",
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

    def test_alerts_aggregated_and_severity_counts(self):
        result, _ = orchestrate.run_pipeline()
        assert isinstance(result["alerts_aggregated"], list)
        assert result["alerts_aggregated"], "mock logs must produce alerts"
        for agg in result["alerts_aggregated"]:
            assert agg["count"] >= 1
            assert agg["severity"] in ("INFO", "WARNING", "CRITICAL")
            assert agg["key"]
        counts = result["severity_counts"]
        assert counts["CRITICAL"] >= 1
        assert counts["WARNING"] >= 1
        assert sum(counts.values()) == len(result["alerts_aggregated"])

    def test_history_flags_recurring_alert(self):
        first, _ = orchestrate.run_pipeline()
        from alerting import AlertAggregator

        history = AlertAggregator.history_from_snapshot(first)
        second, _ = orchestrate.run_pipeline(history=history)
        recurring = [a for a in second["alerts_aggregated"] if a["recurring"]]
        assert recurring, "repeated pipeline must flag at least one recurring alert"


class TestShadowMode:
    def test_mock_snapshot_has_enabled_shadow_mode(self):
        result, _ = orchestrate.run_pipeline()
        shadow = result["shadow_mode"]
        assert shadow["enabled"] is True
        assert 0 <= shadow["ml_risk"] <= 1
        assert isinstance(shadow["agreement"], bool)
        assert shadow["verdict"] in ("AGREE", "DISAGREE")
        assert shadow["forecast"]["predicted"]
        assert isinstance(shadow["anomalies"]["count"], int)
        assert shadow["series"] == [1.0, 1.0, 1.0]

    def test_shadow_mode_does_not_change_heuristic_result(self):
        result, raw_logs = orchestrate.run_pipeline()
        from collector import LogCollector
        from heuristic import HeuristicEngine

        logs = LogCollector().load(raw_logs)
        analysis = HeuristicEngine().analyze([log.model_dump() for log in logs])
        assert result["risk_score"] == analysis["risk_score"]
        assert result["alerts"] == analysis["alerts"]
        assert result["health_check"] is not None

    def test_shadow_disabled_without_series_points(self):
        client = FakeMCPClient([])
        result, _ = orchestrate.run_pipeline(mode="real", client=client)
        assert result["shadow_mode"]["enabled"] is False
        assert "reason" in result["shadow_mode"]


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
        monkeypatch.setattr(sys, "argv", ["orchestrate.py", "--mode", "bogus"])
        try:
            orchestrate.main()
            raise AssertionError("expected SystemExit")
        except SystemExit as e:
            assert e.code == 2

    def test_raises_when_pipeline_result_missing_keys(self, tmp_path, monkeypatch):
        def stub_run_pipeline(
            *,
            mode="mock",
            client=None,
            history=None,
            prev_snapshot=None,
            feedback_file=None,
        ):
            return ({"risk_score": 0.5}, [])

        monkeypatch.setattr(orchestrate, "run_pipeline", stub_run_pipeline)
        output = tmp_path / "output.json"
        monkeypatch.setattr(sys, "argv", ["orchestrate.py", "--log-file", str(output)])
        try:
            orchestrate.main()
            raise AssertionError("expected ValueError")
        except ValueError as e:
            assert "missing required keys" in str(e)

    def test_raises_when_risk_score_out_of_range(self, tmp_path, monkeypatch):
        bad_result = {"risk_score": 1.5, "alerts": [], "health_check": {}}

        def stub_run_pipeline(
            *,
            mode="mock",
            client=None,
            history=None,
            prev_snapshot=None,
            feedback_file=None,
        ):
            return (bad_result, [])

        monkeypatch.setattr(orchestrate, "run_pipeline", stub_run_pipeline)
        output = tmp_path / "output.json"
        monkeypatch.setattr(sys, "argv", ["orchestrate.py", "--log-file", str(output)])
        try:
            orchestrate.main()
            raise AssertionError("expected ValueError")
        except ValueError as e:
            assert "out of range" in str(e)


class FakeMCPClient:
    """MCP client stub for real-mode tests (no network)."""

    def __init__(self, records):
        self._records = records
        self.calls = []

    def query(self, soql):
        self.calls.append(soql)
        return {"records": self._records}


class TestMapSoqlRecords:
    def test_maps_basic_fields(self):
        records = [
            {
                "Id": "a00X000001",
                "CreatedDate": "2026-08-16T10:00:00.000Z",
                "Status": "500",
                "DurationMilliseconds": 1500,
                "Application": "ORG-X",
            }
        ]
        mapped = orchestrate.map_soql_records(records)
        assert mapped[0]["log_id"] == "a00X000001"
        assert mapped[0]["timestamp"] == "2026-08-16T10:00:00.000Z"
        assert mapped[0]["status_code"] == 500
        assert mapped[0]["duration_ms"] == 1500
        assert mapped[0]["org_id"] == "ORG-X"
        assert mapped[0]["severity"] == "ERROR"

    def test_handles_missing_fields_gracefully(self):
        mapped = orchestrate.map_soql_records([{}])
        assert mapped[0]["log_id"] == ""
        assert mapped[0]["status_code"] == 0
        assert mapped[0]["duration_ms"] == 0
        assert mapped[0]["severity"] == "INFO"

    def test_info_severity_for_2xx_status(self):
        mapped = orchestrate.map_soql_records(
            [{"Id": "L1", "Status": "200", "DurationMilliseconds": "50"}]
        )
        assert mapped[0]["severity"] == "INFO"
        assert mapped[0]["status_code"] == 200

    def test_maps_real_log_schema_with_float_status(self):
        records = [
            {
                "Id": "a05bL000004jKLIQA2",
                "CreatedDate": "2026-08-16T10:00:00.000Z",
                "Status__c": 500.0,
                "Endpoint__c": "/api/accounts",
                "WebserviceName__c": "AccountsService",
            }
        ]
        mapped = orchestrate.map_soql_records(records)
        assert mapped[0]["log_id"] == "a05bL000004jKLIQA2"
        assert mapped[0]["status_code"] == 500
        assert mapped[0]["resource"] == "/api/accounts"
        assert mapped[0]["severity"] == "ERROR"

    def test_maps_real_log_extra_fields(self):
        records = [
            {
                "Id": "a05bL000004jKLIQA2",
                "CreatedDate": "2026-08-16T10:00:00.000Z",
                "Status__c": 500.0,
                "Endpoint__c": "/api/accounts",
                "Message__c": "Timeout calling external API",
                "Retried__c": True,
                "Object__c": "Account",
                "ObjectId__c": "001XX0001",
            }
        ]
        mapped = orchestrate.map_soql_records(records)
        assert mapped[0]["message"] == "Timeout calling external API"
        assert mapped[0]["retried"] is True
        assert mapped[0]["object_name"] == "Account"
        assert mapped[0]["object_id"] == "001XX0001"

    def test_retried_accepts_string_and_numeric_values(self):
        assert orchestrate._to_bool(True) is True
        assert orchestrate._to_bool(False) is False
        assert orchestrate._to_bool("true") is True
        assert orchestrate._to_bool("1") is True
        assert orchestrate._to_bool("false") is False
        assert orchestrate._to_bool(0) is False
        assert orchestrate._to_bool(None) is False
        assert orchestrate._to_bool("") is False

    def test_build_soql_query_uses_absolute_window_start(self):
        query = orchestrate.build_soql_query("2026-08-16T19:00:00Z")
        assert "CreatedDate >= 2026-08-16T19:00:00Z" in query
        assert "LAST_N_HOURS" not in query

    def test_float_2xx_status_is_info(self):
        mapped = orchestrate.map_soql_records(
            [{"Id": "L1", "Status__c": 200.0, "Endpoint__c": "/api/health"}]
        )
        assert mapped[0]["status_code"] == 200
        assert mapped[0]["severity"] == "INFO"
        assert mapped[0]["resource"] == "/api/health"

    def test_to_int_handles_numeric_strings_and_garbage(self):
        assert orchestrate._to_int(None) == 0
        assert orchestrate._to_int(500.0) == 500
        assert orchestrate._to_int("200") == 200
        assert orchestrate._to_int("abc") == 0


class TestRunPipelineRealMode:
    def test_uses_mcp_client_to_fetch_logs(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        records = [
            {
                "Id": "log-1",
                "CreatedDate": f"{today}T10:00:00Z",
                "Status": "200",
                "DurationMilliseconds": 100,
                "Application": "ORG-REAL",
            },
            {
                "Id": "log-2",
                "CreatedDate": f"{today}T10:01:00Z",
                "Status": "500",
                "DurationMilliseconds": 2000,
                "Application": "ORG-REAL",
            },
        ]
        client = FakeMCPClient(records)
        result, raw_logs = orchestrate.run_pipeline(mode="real", client=client)
        assert len(client.calls) == 1
        assert "FROM Log__c" in client.calls[0]
        assert f"CreatedDate >= {today}T" in client.calls[0]
        assert "LAST_N_HOURS" not in client.calls[0]
        assert raw_logs[0]["log_id"] == "log-1"
        assert result["mode"] == "real"
        assert result["logs_processed"] == 2
        assert 0 <= result["risk_score"] <= 1

    def test_empty_records_returns_zero_logs_pipeline(self):
        client = FakeMCPClient([])
        result, raw_logs = orchestrate.run_pipeline(mode="real", client=client)
        assert raw_logs == []
        assert result["logs_processed"] == 0

    def test_handles_client_returning_string_payload(self):
        import json as _json

        payload = {
            "records": [{"Id": "L1", "Status": "500", "DurationMilliseconds": 1500}]
        }
        client = FakeMCPClient.__new__(FakeMCPClient)
        client.calls = []
        client.query = lambda soql: _json.dumps(payload)
        result, raw_logs = orchestrate.run_pipeline(mode="real", client=client)
        assert raw_logs[0]["log_id"] == "L1"


class TestFeedbackLoop:
    """Phase 4: accuracy evaluation (Step 6) and feedback ingestion (Step 7)."""

    def test_accuracy_absent_without_prev_snapshot(self):
        result, _ = orchestrate.run_pipeline()
        assert "accuracy" not in result

    def test_accuracy_evaluated_with_prev_shadow_snapshot(self):
        prev = {
            "timestamp": "2026-08-16T10:00:00+00:00",
            "shadow_mode": {
                "enabled": True,
                "forecast": {"slope": 2.0, "intercept": 1.0},
                "anomalies": {"count": 0},
                "series": [0.0, 1.0, 2.0],
            },
        }
        result, _ = orchestrate.run_pipeline(prev_snapshot=prev)
        accuracy = result["accuracy"]
        assert accuracy["status"] == "evaluated"
        assert accuracy["direction_expected"] in ("up", "down", "flat")
        assert "series_actual" in accuracy

    def test_accuracy_no_data_when_prev_without_shadow(self):
        result, _ = orchestrate.run_pipeline(prev_snapshot={"risk_score": 0.1})
        assert result["accuracy"]["status"] == "no_data"

    def test_feedback_summary_present_with_file(self, tmp_path):
        feedback_path = tmp_path / "feedback.json"
        feedback_path.write_text(
            json.dumps(
                [
                    {"id": "a1", "target": "anomaly", "action": "true_positive"},
                    {"id": "a2", "target": "anomaly", "action": "false_positive"},
                ]
            )
        )
        result, _ = orchestrate.run_pipeline(feedback_file=str(feedback_path))
        summary = result["feedback_summary"]
        assert summary["loaded"] == 2
        assert summary["valid"] == 2
        assert summary["invalid"] == 0
        assert summary["by_action"] == {"true_positive": 1, "false_positive": 1}
        assert summary["by_target"] == {"anomaly": 2}

    def test_feedback_summary_absent_without_file(self):
        result, _ = orchestrate.run_pipeline()
        assert "feedback_summary" not in result

    def test_invalid_feedback_rows_do_not_break_pipeline(self, tmp_path):
        feedback_path = tmp_path / "feedback.json"
        feedback_path.write_text(
            json.dumps(
                [
                    {"id": "ok", "target": "alert", "action": "true_positive"},
                    {"id": 42, "target": "alert", "action": "true_positive"},
                    "garbage",
                ]
            )
        )
        result, _ = orchestrate.run_pipeline(feedback_file=str(feedback_path))
        assert result["feedback_summary"]["valid"] == 1
        assert result["feedback_summary"]["invalid"] == 2

    def test_missing_feedback_file_is_captured_as_step_error(self, tmp_path):
        result, _ = orchestrate.run_pipeline(feedback_file=str(tmp_path / "nope.json"))
        assert "feedback_summary" not in result
        assert result["pipeline"]["step_errors"][0]["step"] == "feedback"


class TestHardening:
    """Phase 5: pipeline metadata, step isolation, Sentry opt-in."""

    def test_pipeline_block_present_in_mock_run(self):
        result, _ = orchestrate.run_pipeline()
        pipeline = result["pipeline"]
        assert pipeline["duration_ms"] >= 0
        assert pipeline["steps"] == [
            "collect",
            "analyze",
            "aggregate",
            "compare",
            "shadow",
        ]
        assert pipeline["step_errors"] == []

    def test_steps_include_optional_when_requested(self, tmp_path):
        feedback_path = tmp_path / "feedback.json"
        feedback_path.write_text("[]")
        result, _ = orchestrate.run_pipeline(
            prev_snapshot={"risk_score": 0.1}, feedback_file=str(feedback_path)
        )
        assert "accuracy" in result["pipeline"]["steps"]
        assert "feedback" in result["pipeline"]["steps"]

    def test_shadow_failure_is_captured_not_fatal(self, monkeypatch):
        def boom(raw_logs, heuristic_risk):
            raise RuntimeError("ml engine exploded")

        monkeypatch.setattr(orchestrate, "_run_shadow", boom)
        result, _ = orchestrate.run_pipeline()
        assert result["shadow_mode"] == {
            "enabled": False,
            "reason": "shadow step failed",
        }
        assert result["pipeline"]["step_errors"] == [
            {"step": "shadow", "error": "RuntimeError: ml engine exploded"}
        ]
        assert "risk_score" in result

    def test_compare_failure_is_captured_not_fatal(self, monkeypatch):
        import comparison

        class BrokenComparison:
            def compare(self, analysis):
                raise RuntimeError("comparison exploded")

        monkeypatch.setattr(comparison, "ComparisonService", BrokenComparison)
        result, _ = orchestrate.run_pipeline()
        assert result["comparison"]["prediction"] is None
        assert result["comparison"]["summary"].startswith("comparison step failed")
        assert result["pipeline"]["step_errors"][0]["step"] == "compare"

    def test_collect_failure_is_fatal(self, monkeypatch):
        import pytest

        def boom(client):
            raise RuntimeError("mcp down")

        monkeypatch.setattr(orchestrate, "fetch_real_logs", boom)
        client = FakeMCPClient([])
        with pytest.raises(RuntimeError, match="mcp down"):
            orchestrate.run_pipeline(mode="real", client=client)

    def test_analyze_failure_is_fatal(self, monkeypatch):
        import heuristic
        import pytest

        class BrokenEngine:
            def analyze(self, logs):
                raise RuntimeError("heuristic exploded")

        monkeypatch.setattr(heuristic, "HeuristicEngine", BrokenEngine)
        with pytest.raises(RuntimeError, match="heuristic exploded"):
            orchestrate.run_pipeline()

    def test_aggregate_failure_is_fatal(self, monkeypatch):
        import alerting
        import pytest

        class BrokenAggregator:
            def aggregate(self, alerts, history=None):
                raise RuntimeError("aggregator exploded")

            def severity_counts(self, aggregated):
                raise RuntimeError("aggregator exploded")

        monkeypatch.setattr(alerting, "AlertAggregator", BrokenAggregator)
        with pytest.raises(RuntimeError, match="aggregator exploded"):
            orchestrate.run_pipeline()

    def test_sentry_init_noop_without_dsn(self, monkeypatch):
        monkeypatch.delenv("SENTRY_DSN", raising=False)
        assert orchestrate.init_sentry() is False

    def test_sentry_init_with_dsn(self, monkeypatch):
        calls = {}

        class FakeSentry:
            @staticmethod
            def init(**kwargs):
                calls["init"] = kwargs

        monkeypatch.setenv("SENTRY_DSN", "https://fake@sentry.example/1")
        monkeypatch.setitem(sys.modules, "sentry_sdk", FakeSentry)
        assert orchestrate.init_sentry() is True
        assert calls["init"]["dsn"] == "https://fake@sentry.example/1"
        assert calls["init"]["traces_sample_rate"] == 0.0

    def test_main_writes_metrics_file(self, tmp_path, monkeypatch):
        output = tmp_path / "output.json"
        metrics = tmp_path / "metrics.prom"
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "orchestrate.py",
                "--log-file",
                str(output),
                "--metrics-file",
                str(metrics),
            ],
        )
        orchestrate.main()
        assert metrics.exists()
        content = metrics.read_text()
        assert "monitoring_risk_score" in content
        assert "monitoring_pipeline_info" in content

    def test_main_captures_exception_when_sentry_active(self, tmp_path, monkeypatch):
        calls = {"capture": 0}

        class FakeSentry:
            @staticmethod
            def init(**kwargs):
                pass

            @staticmethod
            def capture_exception():
                calls["capture"] += 1

        monkeypatch.setenv("SENTRY_DSN", "https://fake@sentry.example/1")
        monkeypatch.setitem(sys.modules, "sentry_sdk", FakeSentry)

        def stub_run_pipeline(
            *,
            mode="mock",
            client=None,
            history=None,
            prev_snapshot=None,
            feedback_file=None,
        ):
            return ({"risk_score": 0.5}, [])

        monkeypatch.setattr(orchestrate, "run_pipeline", stub_run_pipeline)
        output = tmp_path / "output.json"
        monkeypatch.setattr(sys, "argv", ["orchestrate.py", "--log-file", str(output)])
        try:
            orchestrate.main()
            raise AssertionError("expected ValueError")
        except ValueError:
            pass
        assert calls["capture"] == 1

    def test_main_reraise_without_sentry(self, tmp_path, monkeypatch):
        monkeypatch.delenv("SENTRY_DSN", raising=False)

        def stub_run_pipeline(
            *,
            mode="mock",
            client=None,
            history=None,
            prev_snapshot=None,
            feedback_file=None,
        ):
            return ({"risk_score": 0.5}, [])

        monkeypatch.setattr(orchestrate, "run_pipeline", stub_run_pipeline)
        output = tmp_path / "output.json"
        monkeypatch.setattr(sys, "argv", ["orchestrate.py", "--log-file", str(output)])
        try:
            orchestrate.main()
            raise AssertionError("expected ValueError")
        except ValueError:
            pass
