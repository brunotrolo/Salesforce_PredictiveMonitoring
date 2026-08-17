import pytest
from alerting import AlertAggregator


@pytest.fixture
def service():
    return AlertAggregator()


@pytest.fixture
def sample_alerts():
    return [
        {
            "severity": "CRITICAL",
            "kind": "error",
            "resource": "/api/users",
            "message": "Error on /api/users: status 500",
            "log_id": "L1",
            "timestamp": "2026-08-16T12:00:00Z",
        },
        {
            "severity": "CRITICAL",
            "kind": "error",
            "resource": "/api/users",
            "message": "Error on /api/users: status 500",
            "log_id": "L2",
            "timestamp": "2026-08-16T12:01:00Z",
        },
        {
            "severity": "WARNING",
            "kind": "slow",
            "resource": "/api/products",
            "message": "Slow request on /api/products: 1500ms",
            "log_id": "L3",
            "timestamp": "2026-08-16T12:02:00Z",
        },
    ]
