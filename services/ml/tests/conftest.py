import pytest


@pytest.fixture
def series_with_outlier():
    return [0.0, 0.0, 0.0, 0.0, 100.0]
