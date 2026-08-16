import pytest
import yaml


@pytest.fixture
def mock_logs():
    with open("tests/fixtures/mock_logs.yaml") as f:
        return yaml.safe_load(f)["logs"]


@pytest.fixture
def collector_service():
    from collector import LogCollector

    return LogCollector()


@pytest.fixture
def single_valid_log():
    return {
        "log_id": "LOG-TEST",
        "timestamp": "2026-08-15T10:00:00Z",
        "org_id": "ORG-TEST",
        "status_code": 200,
        "duration_ms": 100,
        "resource": "/api/test",
    }


@pytest.fixture
def invalid_log():
    return {"log_id": "BAD-LOG"}
