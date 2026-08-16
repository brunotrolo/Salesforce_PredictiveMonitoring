import pytest
from src.comparison import ComparisonService, ComparisonResult


@pytest.fixture
def service():
    return ComparisonService()


@pytest.fixture
def current_high_risk():
    return {"risk_score": 0.8, "errors_count": 5, "slow_count": 3}


@pytest.fixture
def historical_baseline():
    return {"risk_score": 0.2, "errors_count": 1, "slow_count": 1}
