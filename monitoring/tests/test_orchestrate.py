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
        monkeypatch.setattr(sys, "argv", ["orchestrate.py", "--mode", "bogus"])
        try:
            orchestrate.main()
            raise AssertionError("expected SystemExit")
        except SystemExit as e:
            assert e.code == 2

    def test_raises_when_pipeline_result_missing_keys(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            orchestrate, "run_pipeline", lambda mode="mock": ({"risk_score": 0.5}, [])
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
        monkeypatch.setattr(
            orchestrate, "run_pipeline", lambda mode="mock": (bad_result, [])
        )
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
        records = [
            {
                "Id": "log-1",
                "CreatedDate": "2026-08-16T10:00:00Z",
                "Status": "200",
                "DurationMilliseconds": 100,
                "Application": "ORG-REAL",
            },
            {
                "Id": "log-2",
                "CreatedDate": "2026-08-16T10:01:00Z",
                "Status": "500",
                "DurationMilliseconds": 2000,
                "Application": "ORG-REAL",
            },
        ]
        client = FakeMCPClient(records)
        result, raw_logs = orchestrate.run_pipeline(mode="real", client=client)
        assert client.calls == [orchestrate.SOQL_LOG_QUERY]
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
