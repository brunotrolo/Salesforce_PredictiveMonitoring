import pytest


@pytest.fixture
def prev_snapshot_with_shadow():
    """Snapshot anterior (N-1) com shadow_mode avaliável: previu subida
    (slope > 0) e sinalizou anomalia."""
    return {
        "timestamp": "2026-08-16T10:00:00+00:00",
        "risk_score": 0.5,
        "shadow_mode": {
            "enabled": True,
            "heuristic_risk": 0.5,
            "ml_risk": 0.6,
            "agreement": True,
            "verdict": "AGREE",
            "forecast": {"slope": 2.0, "intercept": 1.0, "predicted": [7.0, 9.0, 11.0]},
            "anomalies": {"outliers": [{"index": 4, "value": 100.0}], "count": 1},
            "series": [0.0, 0.0, 0.0, 0.0, 100.0],
        },
    }


@pytest.fixture
def current_snapshot_series_up():
    """Série atual (N) confirmando a subida: último ponto bem acima do
    primeiro, pico sustentado acima do baseline anterior."""
    return {
        "timestamp": "2026-08-16T10:05:00+00:00",
        "shadow_mode": {
            "enabled": True,
            "series": [2.0, 4.0, 6.0, 8.0, 10.0, 12.0],
        },
    }


@pytest.fixture
def current_snapshot_series_flat():
    """Série atual (N) plana: direção não confirmou (era up), pico sumiu."""
    return {
        "timestamp": "2026-08-16T10:05:00+00:00",
        "shadow_mode": {
            "enabled": True,
            "series": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        },
    }
