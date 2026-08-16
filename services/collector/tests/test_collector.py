"""Tests for Collector service - LogCollector."""

from src.collector import SalesforceLog


class TestLogCollectorLoad:
    def test_loads_mock_logs(self, collector_service, mock_logs):
        result = collector_service.load(mock_logs)
        assert len(result) == 3
        assert result[0].log_id == "LOG-001"

    def test_load_returns_salesforce_log_models(self, collector_service, mock_logs):
        result = collector_service.load(mock_logs)
        for log in result:
            assert isinstance(log, SalesforceLog)

    def test_load_empty_list(self, collector_service):
        result = collector_service.load([])
        assert result == []

    def test_load_single_log(self, collector_service, single_valid_log):
        result = collector_service.load([single_valid_log])
        assert len(result) == 1
        assert result[0].log_id == "LOG-TEST"


class TestLogCollectorValidate:
    def test_validates_all_valid(self, collector_service, mock_logs):
        result = collector_service.validate(mock_logs)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_validates_with_errors(
        self, collector_service, invalid_log, single_valid_log
    ):
        result = collector_service.validate([single_valid_log, invalid_log])
        assert result["valid"] is False
        assert len(result["errors"]) == 1

    def test_validates_empty_list(self, collector_service):
        result = collector_service.validate([])
        assert result["valid"] is True
        assert result["errors"] == []


class TestSalesforceLogModel:
    def test_default_severity(self):
        log = SalesforceLog(
            log_id="L1",
            timestamp="2026-01-01T00:00:00Z",
            org_id="O1",
            status_code=200,
            duration_ms=100,
            resource="/r",
        )
        assert log.severity == "INFO"

    def test_custom_severity(self):
        log = SalesforceLog(
            log_id="L1",
            timestamp="2026-01-01T00:00:00Z",
            org_id="O1",
            status_code=500,
            duration_ms=2000,
            resource="/r",
            severity="ERROR",
        )
        assert log.severity == "ERROR"
