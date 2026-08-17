"""Prometheus text exposition (Phase 5) — snapshot -> scrapeable metrics."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

_LABEL_SAFE = re.compile(r"[^a-zA-Z0-9_:]")

_SERIES: tuple[tuple[str, str], ...] = (
    ("risk_score", "Heuristic risk score (0..1)"),
    ("errors_count", "Errors observed in the window"),
    ("slow_requests_count", "Slow requests in the window"),
    ("retried_count", "Requests that were retried in the window"),
    ("logs_processed", "Logs processed in the window"),
    ("pipeline_duration_ms", "Pipeline cycle duration in milliseconds"),
    ("pipeline_step_errors_count", "Pipeline steps that failed in the cycle"),
    ("cycle_timestamp_seconds", "Cycle timestamp (Unix seconds)"),
)


def _sanitize_label(value: Any) -> str:
    """Keep Prometheus labels within the [a-zA-Z0-9_:] alphabet."""
    return _LABEL_SAFE.sub("_", str(value))


def _to_number(value: Any) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return 0.0


def _timestamp_seconds(iso: str) -> float:
    if not iso:
        return 0.0
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def build_prometheus_metrics(snapshot: dict[str, Any]) -> str:
    """Render a pipeline snapshot in Prometheus text exposition format."""
    lines: list[str] = []

    mode = _sanitize_label(snapshot.get("mode", "unknown"))
    health_check = snapshot.get("health_check") or {}
    health = _sanitize_label(health_check.get("status", "UNKNOWN"))
    lines.append("# HELP monitoring_pipeline_info Pipeline cycle metadata")
    lines.append("# TYPE monitoring_pipeline_info gauge")
    lines.append(f'monitoring_pipeline_info{{mode="{mode}",health="{health}"}} 1')

    pipeline = snapshot.get("pipeline") or {}
    for key, help_text in _SERIES:
        if key == "cycle_timestamp_seconds":
            value = _timestamp_seconds(snapshot.get("timestamp", ""))
        elif key == "pipeline_duration_ms":
            value = _to_number(pipeline.get("duration_ms", 0))
        elif key == "pipeline_step_errors_count":
            value = _to_number(len(pipeline.get("step_errors", [])))
        else:
            value = _to_number(snapshot.get(key, 0))
        lines.append(f"# HELP monitoring_{key} {help_text}")
        lines.append(f"# TYPE monitoring_{key} gauge")
        lines.append(f"monitoring_{key} {value:g}")

    severity_counts = snapshot.get("severity_counts") or {}
    if severity_counts:
        lines.append("# HELP monitoring_alerts_total Active alerts by severity")
        lines.append("# TYPE monitoring_alerts_total gauge")
        for severity, count in sorted(severity_counts.items()):
            safe = _sanitize_label(severity)
            value = _to_number(count)
            lines.append(f'monitoring_alerts_total{{severity="{safe}"}} {value:g}')

    shadow = snapshot.get("shadow_mode")
    if isinstance(shadow, dict) and shadow.get("enabled"):
        lines.append("# HELP monitoring_shadow_ml_risk ML shadow-mode risk score")
        lines.append("# TYPE monitoring_shadow_ml_risk gauge")
        value = _to_number(shadow.get("ml_risk", 0))
        lines.append(f"monitoring_shadow_ml_risk {value:g}")

    return "\n".join(lines) + "\n"
