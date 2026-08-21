#!/usr/bin/env python
"""Monitoring pipeline orchestrator - Phase 0 (Mock) + Phase 1 (Real MCP)."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
from datetime import datetime, timedelta, timezone
from typing import Any

# SOQL query used in real (Phase 1) mode: integration logs from the last hour.
# Field-API names follow the actual Log__c schema in the org (verified via
# getObjectSchema on 2026-08-16): Status__c (double), Endpoint__c,
# Method__c, WebserviceName__c, Message__c, Retried__c, Object__c,
# ObjectId__c. There is no duration field on Log__c (no Nebula Logger yet),
# so duration_ms stays 0 and slow-request detection is inactive until the
# Nebula schema lands. The window is a computed absolute timestamp, NOT
# LAST_N_HOURS:1 (the MCP soqlQuery parser rejects that function - observed
# 2026-08-16, MALFORMED_QUERY "unexpected token: 'LAST_N_HOURS'").
SOQL_LOG_QUERY = (
    "SELECT Id, CreatedDate, Status__c, Endpoint__c, Method__c, "
    "WebserviceName__c, Message__c, Retried__c, Object__c, ObjectId__c, "
    "SystemModstamp "
    "FROM Log__c "
    "WHERE CreatedDate >= {window_start} "
    "ORDER BY CreatedDate DESC LIMIT 100"
)
WINDOW_HOURS = 1

# Rolling 24h trace: entries older than this window are pruned on each cycle.
TRACE_WINDOW_HOURS = 24

# Messages that signal a circuit breaker (Salesforce integration patterns):
# explicit breaker events, HTTP 429/503, rate limiting and timeouts. Matched
# case-insensitively against Log__c Message__c and alert messages.
CIRCUIT_BREAKER_PATTERNS = (
    "circuit breaker",
    "circuitbreaker",
    "breaker open",
    "429",
    "503",
    "rate limit",
    "too many requests",
    "timeout",
)


def build_soql_query(window_start: str) -> str:
    """Build the SOQL query with an absolute window start (ISO UTC, ``Z``)."""
    return SOQL_LOG_QUERY.format(window_start=window_start)


def generate_mock_logs() -> list[dict]:
    """Generate mock Salesforce logs for testing.

    Timestamps are spread across the last minutes so the ML shadow mode
    (Phase 3) has a real series to analyze: [1, 1, 1] counts per minute.
    """
    now = datetime.now(timezone.utc)
    minutes = [now - timedelta(minutes=2), now - timedelta(minutes=1), now]
    return [
        {
            "log_id": "L1",
            "status_code": 200,
            "duration_ms": 100,
            "timestamp": minutes[0].isoformat(),
            "org_id": "ORG-MOCK",
            "resource": "/api/accounts",
        },
        {
            "log_id": "L2",
            "status_code": 500,
            "duration_ms": 1500,
            "timestamp": minutes[1].isoformat(),
            "org_id": "ORG-MOCK",
            "resource": "/api/users",
        },
        {
            "log_id": "L3",
            "status_code": 200,
            "duration_ms": 200,
            "timestamp": minutes[2].isoformat(),
            "org_id": "ORG-MOCK",
            "resource": "/api/products",
        },
    ]


def _to_int(value: Any) -> int:
    """Coerce a Salesforce value (int, float, numeric string) to int."""
    if value is None:
        return 0
    try:
        return int(float(value))
    except TypeError, ValueError:
        return 0


def _to_bool(value: Any) -> bool:
    """Coerce a Salesforce boolean-ish value to bool ('' / 0 / 'false' -> False)."""
    if value is None or value == "":
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in ("true", "1", "yes", "sim")


def map_soql_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map Salesforce SOQL records to the collector's internal log schema.

    Accepts both the real Log__c schema (``Status__c`` as double,
    ``Endpoint__c``/``WebserviceName__c`` for the resource) and the legacy
    debug-log field names (``Status``, ``DurationMilliseconds``,
    ``Application``) for compatibility.
    """
    mapped: list[dict[str, Any]] = []
    for rec in records:
        status = rec.get("Status__c", rec.get("Status", rec.get("StatusCode__c", 0)))
        duration = rec.get("DurationMilliseconds", rec.get("Duration_ms__c", 0))
        resource = (
            rec.get("Endpoint__c")
            or rec.get("WebserviceName__c")
            or rec.get("Method__c")
            or str(rec.get("SystemModstamp", "unknown"))
        )
        mapped.append(
            {
                "log_id": str(rec.get("Id", "")),
                "timestamp": str(rec.get("CreatedDate", "")),
                "org_id": str(
                    rec.get("OrganizationId__c", rec.get("Application", "ORG-REAL"))
                ),
                "status_code": _to_int(status),
                "duration_ms": _to_int(duration),
                "resource": str(resource),
                "severity": "ERROR" if _to_int(status) >= 500 else "INFO",
                "message": str(rec.get("Message__c", "")),
                "retried": _to_bool(rec.get("Retried__c")),
                "object_name": str(rec.get("Object__c", "")),
                "object_id": str(rec.get("ObjectId__c", "")),
            }
        )
    return mapped


def fetch_real_logs(client: Any) -> list[dict[str, Any]]:
    """Fetch logs from Salesforce via MCP and map to collector schema."""
    now = datetime.now(timezone.utc)
    window_start = (now - timedelta(hours=WINDOW_HOURS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw = client.query(build_soql_query(window_start))
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError, TypeError:
            return []
    if isinstance(raw, dict) and "records" in raw:
        return map_soql_records(raw["records"])
    if isinstance(raw, list):
        return map_soql_records(raw)
    return []


def _trace_entry_from_result(result: dict, snapshot_name: str | None = None) -> dict:
    """Build one rolling-trace entry from a completed pipeline snapshot.

    The entry is deliberately lean: everything the dashboard needs to answer
    "did the system fall / did the ML flag anomalies / did the log system
    detect a circuit breaker" over the last 24h, without the full snapshot.

    ``snapshot_name`` (e.g. ``2026-08-19T03-37-55Z.json``) is the file the
    caller persists to the data branch; the entry links back to it so every
    conclusion drawn by the dashboard can be traced to its source snapshot.
    """
    shadow = result.get("shadow_mode") or {}
    shadow_enabled = shadow.get("enabled") is True
    breaker_hits: list[str] = []
    for message in [log.get("message", "") for log in result.get("logs") or []] + [
        alert.get("message", "") for alert in result.get("alerts") or []
    ]:
        lowered = str(message).lower()
        if any(pattern in lowered for pattern in CIRCUIT_BREAKER_PATTERNS):
            if str(message) not in breaker_hits:
                breaker_hits.append(str(message))

    error_endpoints: dict[str, dict[str, Any]] = {}
    for log in result.get("logs") or []:
        if _to_int(log.get("status_code", 0)) < 500:
            continue
        resource = str(log.get("resource", "unknown"))
        agg = error_endpoints.setdefault(
            resource, {"count": 0, "max_duration_ms": 0, "sample_message": ""}
        )
        agg["count"] += 1
        agg["max_duration_ms"] = max(
            agg["max_duration_ms"], _to_int(log.get("duration_ms", 0))
        )
        if not agg["sample_message"] and log.get("message"):
            agg["sample_message"] = str(log["message"])[:160]

    snapshot_path = None
    if snapshot_name:
        ts = result.get("timestamp")
        date_part = str(ts)[:10] if ts else None
        if date_part:
            snapshot_path = f"data/{date_part}/{snapshot_name}"

    return {
        "timestamp": result.get("timestamp"),
        "risk_score": result.get("risk_score"),
        "errors_count": result.get("errors_count", 0),
        "retried_count": result.get("retried_count", 0),
        "alerts_critical": (result.get("severity_counts") or {}).get("CRITICAL", 0),
        "alerts_warning": (result.get("severity_counts") or {}).get("WARNING", 0),
        "ml_risk": shadow.get("ml_risk") if shadow_enabled else None,
        "anomalies": (
            (shadow.get("anomalies") or {}).get("count", 0) if shadow_enabled else 0
        ),
        "circuit_breaker": len(breaker_hits) > 0,
        "breaker_messages": breaker_hits[:5],
        "snapshot": snapshot_path,
        "snapshot_raw": (
            f"https://raw.githubusercontent.com/brunotrolo/"
            f"Salesforce_PredictiveMonitoring/{snapshot_path}"
            if snapshot_path
            else None
        ),
        "evidence": {
            "error_endpoints": [
                {
                    "resource": resource,
                    "count": agg["count"],
                    "max_duration_ms": agg["max_duration_ms"],
                    "sample_message": agg["sample_message"],
                }
                for resource, agg in sorted(
                    error_endpoints.items(), key=lambda kv: -kv[1]["count"]
                )[:5]
            ],
            "alerts": [
                {
                    "severity": alert.get("severity", "UNKNOWN"),
                    "message": str(alert.get("message", ""))[:160],
                }
                for alert in (result.get("alerts") or [])[:5]
            ],
        },
    }


def update_trace(
    trace: Any,
    result: dict,
    now: datetime | None = None,
    snapshot_name: str | None = None,
) -> list[dict]:
    """Append the current cycle to the rolling trace and prune old entries.

    Keeps entries newer than ``TRACE_WINDOW_HOURS`` (24h), sorted by
    timestamp. A corrupt or missing input trace degrades to an empty list —
    the trace must never break a collection cycle.
    """
    if not isinstance(trace, list):
        trace = []
    trace.append(_trace_entry_from_result(result, snapshot_name=snapshot_name))
    now = now or datetime.now(timezone.utc)
    cutoff = (now - timedelta(hours=TRACE_WINDOW_HOURS)).isoformat()
    kept = [
        entry
        for entry in trace
        if isinstance(entry, dict)
        and entry.get("timestamp")
        and str(entry["timestamp"]) >= cutoff
    ]
    kept.sort(key=lambda entry: str(entry.get("timestamp", "")))
    return kept


def _execute(
    step_errors: list[dict[str, str]], name: str, fn: Any, *, fatal: bool = False
) -> Any:
    """Run a pipeline step; non-fatal failures are recorded, never raised.

    Fatal steps (``fatal=True``) re-raise — a pipeline without logs or
    analysis is meaningless. Observational steps (compare, shadow, accuracy,
    feedback) degrade to ``None`` and the failure is appended to
    ``step_errors`` so the cycle still completes and produces a snapshot.
    """
    try:
        return fn()
    except Exception as exc:
        if fatal:
            raise
        step_errors.append({"step": name, "error": f"{type(exc).__name__}: {exc}"})
        return None


def _run_shadow(
    raw_logs: list[dict], heuristic_risk: float, threshold: float | None = None
) -> dict:
    """Run the ML shadow-mode engines (Phase 3) — observes, never decides.

    ``threshold`` (Phase 4 auto-calibration) is the AnomalyEngine threshold
    recommended by the Calibrator; ``None`` falls back to the engine default.
    """
    from ml import (
        AnomalyEngine,
        ForecastEngine,
        ShadowComparator,
        build_series,
        risk_from_series,
    )

    series = build_series(raw_logs)
    if len(series) < 3:
        return {"enabled": False, "reason": "insufficient series points (need >= 3)"}
    forecast = ForecastEngine().forecast(series)
    if threshold is None:
        engine = AnomalyEngine()
    else:
        engine = AnomalyEngine(threshold=threshold)
    anomalies = engine.detect(series)
    ml_risk = risk_from_series(series, forecast, anomalies)
    shadow = ShadowComparator().compare(heuristic_risk, ml_risk)
    return {
        "enabled": True,
        "heuristic_risk": heuristic_risk,
        "ml_risk": ml_risk,
        "agreement": shadow.agreement,
        "verdict": shadow.verdict,
        "forecast": forecast.model_dump(),
        "anomalies": anomalies.model_dump(),
        "series": [float(v) for v in series],
    }


def _run_calibration(samples_file: str) -> dict:
    """Load accumulated samples and compute this cycle's threshold (Phase 4).

    Auto-calibration (decision 17/08/2026): the Calibrator recommends a new
    AnomalyEngine threshold from observed false-positive rates. With fewer
    than ``min_samples`` observations the status is ``insufficient`` and the
    threshold falls back to the engine default. Observational — the result
    only annotates the snapshot and tunes shadow mode, never ``risk_score``
    or ``alerts``.
    """
    from feedback import Calibrator, SampleStore
    from ml import AnomalyEngine

    samples = SampleStore().load(samples_file)
    result = Calibrator().recommend(samples)
    return {
        "status": result.status,
        "samples": result.samples,
        "avg_fp_rate": result.avg_fp_rate,
        "current_threshold": result.current_threshold,
        "recommended_threshold": result.recommended_threshold,
        "threshold_used": (
            result.recommended_threshold
            if result.status == "recommended"
            else AnomalyEngine().threshold
        ),
    }


def run_pipeline(
    mode: str = "mock",
    client=None,
    history: dict[str, int] | None = None,
    prev_snapshot: dict | None = None,
    feedback_file: str | None = None,
    samples_file: str | None = None,
) -> tuple[dict, list[dict]]:
    """Run the monitoring pipeline: collector -> heuristic -> alerting ->
    comparison -> shadow mode -> accuracy -> feedback.

    ``mode="mock"`` uses synthetic logs (Phase 0).  ``mode="real"`` fetches
    logs from Salesforce via the MCP client (Phase 1).  Pass a ``client``
    with a ``query(soql)`` method to avoid hitting the real MCP in tests.
    ``history`` maps alert keys to the number of previous snapshots where
    they appeared, so recurring alerts are flagged (Phase 2 aggregation).
    Shadow mode (Phase 3) runs the ML engines in parallel and annotates the
    snapshot with ``shadow_mode`` — it observes and compares, it never
    changes the heuristically-computed ``risk_score`` or ``alerts``.
    ``prev_snapshot`` (Phase 4) is the previous full snapshot, used to
    evaluate shadow accuracy against the current series; ``feedback_file``
    is a user-supplied feedback.json consumed by the FeedbackStore. Both are
    optional and observational — neither decides anything.

    Phase 5 hardening: ``collect``, ``analyze`` and ``aggregate`` are fatal
    (no snapshot without them); ``compare``, ``shadow``, ``accuracy`` and
    ``feedback`` are observational — a failure is recorded in
    ``pipeline.step_errors`` and the cycle still completes.
    """
    from alerting import AlertAggregator
    from collector import LogCollector
    from comparison import ComparisonService
    from heuristic import HeuristicEngine

    started = datetime.now(timezone.utc)
    step_errors: list[dict[str, str]] = []

    # Step 1: Collect (fatal - without logs there is no pipeline)
    collector = LogCollector()
    if mode == "real":
        if client is None:
            from mcp_salesforce import SalesforceClient

            client = SalesforceClient()
        raw_logs = _execute(
            step_errors, "collect", lambda: fetch_real_logs(client), fatal=True
        )
    else:
        raw_logs = generate_mock_logs()
    logs = collector.load(raw_logs)
    validation = collector.validate(raw_logs)

    # Step 2: Analyze (fatal - core risk computation)
    engine = HeuristicEngine()
    analysis = _execute(
        step_errors,
        "analyze",
        lambda: engine.analyze([log.model_dump() for log in logs]),
        fatal=True,
    )

    # Step 3: Aggregate & deduplicate alerts (Phase 2; fatal)
    aggregator = AlertAggregator()
    aggregated = _execute(
        step_errors,
        "aggregate",
        lambda: aggregator.aggregate(analysis["alerts"], history=history),
        fatal=True,
    )
    severity_counts = aggregator.severity_counts(aggregated)

    # Step 3b: Notify on CRITICAL alerts (observational - never breaks cycle)
    try:
        from notification.notification import EmailNotifier
        notifier = EmailNotifier()
        now_ts = datetime.now(timezone.utc).isoformat()
        notifier.send_critical_alerts(
            [a.model_dump() for a in aggregated],
            severity_counts,
            now_ts,
        )
    except Exception:
        pass  # observational only

    # Step 4: Compare (observational - never breaks the cycle)
    comparison_result = _execute(
        step_errors, "compare", lambda: ComparisonService().compare(analysis)
    )
    if comparison_result is None:
        comparison = {
            "prediction": None,
            "confidence": 0.0,
            "risk_delta": 0.0,
            "summary": "comparison step failed (see pipeline.step_errors)",
        }
    else:
        comparison = {
            "prediction": comparison_result.prediction,
            "confidence": comparison_result.confidence,
            "risk_delta": comparison_result.risk_delta,
            "summary": comparison_result.summary,
        }

    # Step 5: Shadow mode (Phase 3 - ML observes, never decides)
    # Phase 4 auto-calibration: the recommended threshold from accumulated
    # samples tunes this cycle's anomaly engine (default 3.5 when the
    # calibration is missing or has too few samples).
    calibration: dict | None = None
    if samples_file is not None:
        calibration = _execute(
            step_errors,
            "calibration",
            lambda: _run_calibration(samples_file),
        )
    shadow_threshold = (
        calibration["threshold_used"] if calibration is not None else None
    )
    shadow_mode = _execute(
        step_errors,
        "shadow",
        lambda: _run_shadow(
            raw_logs, analysis["risk_score"], threshold=shadow_threshold
        ),
    )
    if shadow_mode is None:
        shadow_mode = {"enabled": False, "reason": "shadow step failed"}

    # Step 6: Model accuracy (Phase 4 - evaluate previous shadow vs reality)
    accuracy: dict | None = None
    if prev_snapshot is not None:
        from feedback import AccuracyTracker

        accuracy = _execute(
            step_errors,
            "accuracy",
            lambda: (
                AccuracyTracker()
                .evaluate(prev_snapshot, {"shadow_mode": shadow_mode})
                .model_dump()
            ),
        )

    # Phase 4 auto-calibration: record one observation per cycle that flagged
    # an anomaly — the threshold used in the previous cycle and whether the
    # signal turned out to be a false positive. Saved back to the samples
    # file (persisted to the data branch by collect.yml).
    if (
        samples_file is not None
        and calibration is not None
        and accuracy is not None
        and accuracy.get("anomaly_flagged")
    ):
        prev_threshold = (
            (prev_snapshot.get("shadow_mode") or {})
            .get("anomalies", {})
            .get("threshold")
        )
        if (
            isinstance(prev_threshold, (int, float))
            and isinstance(prev_threshold, bool) is False
        ):

            def record_sample():
                from feedback import SampleStore

                store = SampleStore()
                samples = store.add(
                    store.load(samples_file),
                    float(prev_threshold),
                    1.0 if accuracy.get("false_positive") else 0.0,
                )
                store.save(samples_file, samples)

            _execute(step_errors, "calibration", record_sample)

    # Step 7: User feedback ingestion (Phase 4 - observational only)
    feedback_summary: dict | None = None
    if feedback_file is not None:
        from feedback import FeedbackStore

        loaded = _execute(
            step_errors, "feedback", lambda: FeedbackStore().load(feedback_file)
        )
        if loaded is not None:
            feedback_summary = {
                "loaded": loaded.loaded,
                "valid": loaded.valid,
                "invalid": loaded.invalid,
                "by_action": loaded.by_action,
                "by_target": loaded.by_target,
            }

    # Build result
    now = datetime.now(timezone.utc).isoformat()
    duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
    steps = ["collect", "analyze", "aggregate", "compare", "shadow"]
    if samples_file is not None:
        steps.append("calibration")
    if prev_snapshot is not None:
        steps.append("accuracy")
    if feedback_file is not None:
        steps.append("feedback")
    result = {
        "timestamp": now,
        "mode": mode,
        "risk_score": analysis["risk_score"],
        "errors_count": analysis["errors_count"],
        "slow_requests_count": analysis["slow_count"],
        "retried_count": analysis["retried_count"],
        "alerts": analysis["alerts"],
        "alerts_aggregated": [a.model_dump() for a in aggregated],
        "severity_counts": severity_counts,
        "shadow_mode": shadow_mode,
        "comparison": comparison,
        "health_check": {
            "status": "HEALTHY" if analysis["risk_score"] < 0.7 else "WARNING",
            "last_updated": now,
        },
        "validation": validation,
        "logs_processed": len(logs),
        "logs": [log.model_dump() for log in logs],
        "pipeline": {
            "duration_ms": duration_ms,
            "steps": steps,
            "step_errors": step_errors,
        },
    }
    if accuracy is not None:
        result["accuracy"] = accuracy
    if feedback_summary is not None:
        result["feedback_summary"] = feedback_summary
    if calibration is not None:
        result["calibration_summary"] = calibration
    return result, raw_logs


def _build_client() -> Any:
    """Build a real MCP client using SF_* env vars."""
    from mcp_salesforce import SalesforceClient

    return SalesforceClient()


def _write_auth_state(
    path: str, refresh_token: str, initial: str | None = None
) -> None:
    """Persist the current (possibly rotated) refresh token for the next run.

    Salesforce rotates the refresh token on every refresh (Refresh Token
    Rotation is mandatory in this org), so the token that just worked must
    be handed back to the caller (the CI workflow) before the process exits.

    ``refresh_token_initial`` is the token the run started with; the CI
    workflow only updates the SF_REFRESH_TOKEN secret when the two differ,
    so a run that failed before ever refreshing cannot clobber a valid
    secret with an already-used token.
    """
    with open(path, "w") as f:
        json.dump(
            {
                "refresh_token": refresh_token,
                "refresh_token_initial": initial or refresh_token,
            },
            f,
        )


def init_sentry(dsn: str | None = None) -> bool:
    """Initialize Sentry when ``SENTRY_DSN`` is set; no-op (False) otherwise.

    Phase 5 opt-in error tracking: the pipeline never fails because Sentry
    is missing — without a DSN the function returns ``False`` and nothing
    is imported or sent.
    """
    dsn = dsn or os.environ.get("SENTRY_DSN")
    if not dsn:
        return False
    import sentry_sdk

    sentry_sdk.init(dsn=dsn, traces_sample_rate=0.0)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Salesforce Predictive Monitoring Pipeline"
    )
    parser.add_argument(
        "--mode",
        default="mock",
        choices=["mock", "real"],
        help="Run mode (mock: synthetic logs; real: Salesforce MCP)",
    )
    parser.add_argument(
        "--log-file", default="monitoring_output.json", help="Output JSON file path"
    )
    parser.add_argument(
        "--history-file",
        default=None,
        help=(
            "Previous snapshot JSON used to flag recurring alerts "
            "(Phase 2 aggregation) and evaluate shadow accuracy "
            "(Phase 4); optional"
        ),
    )
    parser.add_argument(
        "--feedback-file",
        default=None,
        help=(
            "User-supplied feedback.json consumed by the FeedbackStore "
            "(Phase 4); optional"
        ),
    )
    parser.add_argument(
        "--samples-file",
        default=None,
        help=(
            "Accumulated calibration samples {threshold, fp_rate} used to "
            "auto-calibrate the shadow AnomalyEngine threshold (Phase 4); "
            "optional"
        ),
    )
    parser.add_argument(
        "--metrics-file",
        default=None,
        help=(
            "Write Prometheus text-format metrics alongside the snapshot "
            "(Phase 5); optional"
        ),
    )
    parser.add_argument(
        "--trace-file",
        default=None,
        help=(
            "Rolling 24h trace JSON: the current cycle is appended and "
            "entries older than 24h are pruned. A missing or corrupt input "
            "file starts fresh; optional"
        ),
    )
    parser.add_argument(
        "--snapshot-name",
        default=None,
        help=(
            "Name of the snapshot file persisted to the data branch "
            "(e.g. 2026-08-19T03-37-55Z.json); each trace entry links back "
            "to it for full traceability. Optional."
        ),
    )
    parser.add_argument(
        "--auth-state-out",
        default=None,
        help=(
            'Write {"refresh_token": ...} after the run, so the caller can '
            "persist the rotated refresh token (Salesforce Refresh Token "
            "Rotation); optional"
        ),
    )
    args = parser.parse_args()

    sentry_active = init_sentry()

    def _classify_error(exc: Exception) -> str:
        msg = str(exc).lower()
        if "invalid_grant" in msg:
            return "auth_token_expired"
        if isinstance(exc, urllib.error.HTTPError) and exc.code == 401:
            return "mcp_unauthorized"
        if isinstance(exc, urllib.error.HTTPError) and exc.code in (429, 500, 502, 503, 504):
            return "mcp_transient"
        if isinstance(exc, (urllib.error.URLError, ConnectionError, OSError)):
            return "transport"
        if isinstance(exc, ValueError):
            return "validation"
        return "unknown"

    client = _build_client() if args.mode == "real" else None
    initial_rt = client.refresh_token if client else None
    try:
        history: dict[str, int] | None = None
        prev_snapshot: dict | None = None
        if args.history_file:
            from alerting import AlertAggregator

            with open(args.history_file) as f:
                prev_snapshot = json.load(f)
            history = AlertAggregator.history_from_snapshot(prev_snapshot)

        result, logs = run_pipeline(
            mode=args.mode,
            client=client,
            history=history,
            prev_snapshot=prev_snapshot,
            feedback_file=args.feedback_file,
            samples_file=args.samples_file,
        )

        # Validate output
        if not {"risk_score", "alerts", "health_check"}.issubset(result):
            raise ValueError("Pipeline result missing required keys")
        if not 0 <= result["risk_score"] <= 1:
            raise ValueError(f"risk_score out of range: {result['risk_score']}")

        # Write JSON output
        with open(args.log_file, "w") as f:
            json.dump(result, f, indent=2)

        if args.metrics_file:
            from metrics import build_prometheus_metrics

            with open(args.metrics_file, "w") as f:
                f.write(build_prometheus_metrics(result))

        if args.trace_file:
            existing: Any = []
            try:
                with open(args.trace_file) as f:
                    existing = json.load(f)
            except OSError, ValueError:
                existing = []
            trace = update_trace(existing, result, snapshot_name=args.snapshot_name)
            with open(args.trace_file, "w") as f:
                json.dump(trace, f, indent=2)

        print(f"Pipeline complete: {args.log_file}")
        print(json.dumps(result, indent=2))
    except Exception as exc:
        if sentry_active:
            import sentry_sdk

            sentry_sdk.capture_exception()
        failure_path = args.log_file + ".failure.json"
        try:
            with open(failure_path, "w") as f:
                json.dump(
                    {
                        "error_type": _classify_error(exc),
                        "message": str(exc)[:1000],
                        "mode": args.mode,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    f,
                    indent=2,
                )
        except OSError:
            pass
        raise
    finally:
        if args.auth_state_out and client is not None and client.refresh_token:
            _write_auth_state(args.auth_state_out, client.refresh_token, initial_rt)


if __name__ == "__main__":
    main()
