import pytest
from src.heuristic import HeuristicEngine, Alert


@pytest.fixture
def engine():
    return HeuristicEngine()


@pytest.fixture
def mixed_logs():
    return [
        {"log_id": "L1", "status_code": 200, "duration_ms": 100, "resource": "/api/a"},
        {"log_id": "L2", "status_code": 500, "duration_ms": 2000, "resource": "/api/b"},
        {"log_id": "L3", "status_code": 200, "duration_ms": 300, "resource": "/api/c"},
    ]


@pytest.fixture
def healthy_logs():
    return [
        {"log_id": "L1", "status_code": 200, "duration_ms": 100, "resource": "/api/a"},
        {"log_id": "L2", "status_code": 200, "duration_ms": 200, "resource": "/api/b"},
    ]


@pytest.fixture
def critical_logs():
    return [
        {"log_id": "L1", "status_code": 500, "duration_ms": 3000, "resource": "/api/a"},
        {"log_id": "L2", "status_code": 503, "duration_ms": 4000, "resource": "/api/b"},
    ]
