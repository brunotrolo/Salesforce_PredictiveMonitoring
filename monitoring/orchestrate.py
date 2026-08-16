#!/usr/bin/env python
"""Monitoring pipeline orchestrator - Phase 0 (Mock) + Phase 1 (Real MCP)."""

from __future__ import annotations

import argparse
import json
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


def build_soql_query(window_start: str) -> str:
    """Build the SOQL query with an absolute window start (ISO UTC, ``Z``)."""
    return SOQL_LOG_QUERY.format(window_start=window_start)


def generate_mock_logs() -> list[dict]:
    """Generate mock Salesforce logs for testing."""
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            "log_id": "L1",
            "status_code": 200,
            "duration_ms": 100,
            "timestamp": now,
            "org_id": "ORG-MOCK",
            "resource": "/api/accounts",
        },
        {
            "log_id": "L2",
            "status_code": 500,
            "duration_ms": 1500,
            "timestamp": now,
            "org_id": "ORG-MOCK",
            "resource": "/api/users",
        },
        {
            "log_id": "L3",
            "status_code": 200,
            "duration_ms": 200,
            "timestamp": now,
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


def run_pipeline(mode: str = "mock", client: Any = None) -> tuple[dict, list[dict]]:
    """Run the monitoring pipeline: collector -> heuristic -> comparison.

    ``mode="mock"`` uses synthetic logs (Phase 0).  ``mode="real"`` fetches
    logs from Salesforce via the MCP client (Phase 1).  Pass a ``client``
    with a ``query(soql)`` method to avoid hitting the real MCP in tests.
    """
    from collector import LogCollector
    from comparison import ComparisonService
    from heuristic import HeuristicEngine

    # Step 1: Collect
    collector = LogCollector()
    if mode == "real":
        if client is None:
            from mcp_salesforce import SalesforceClient

            client = SalesforceClient()
        raw_logs = fetch_real_logs(client)
    else:
        raw_logs = generate_mock_logs()
    logs = collector.load(raw_logs)
    validation = collector.validate(raw_logs)

    # Step 2: Analyze
    engine = HeuristicEngine()
    analysis = engine.analyze([log.model_dump() for log in logs])

    # Step 3: Compare
    comparator = ComparisonService()
    comparison = comparator.compare(analysis)

    # Build result
    now = datetime.now(timezone.utc).isoformat()
    result = {
        "timestamp": now,
        "mode": mode,
        "risk_score": analysis["risk_score"],
        "errors_count": analysis["errors_count"],
        "slow_requests_count": analysis["slow_count"],
        "retried_count": analysis["retried_count"],
        "alerts": analysis["alerts"],
        "comparison": {
            "prediction": comparison.prediction,
            "confidence": comparison.confidence,
            "risk_delta": comparison.risk_delta,
            "summary": comparison.summary,
        },
        "health_check": {
            "status": "HEALTHY" if analysis["risk_score"] < 0.7 else "WARNING",
            "last_updated": now,
        },
        "validation": validation,
        "logs_processed": len(logs),
    }
    return result, raw_logs


def _build_client() -> Any:
    """Build a real MCP client using SF_CLIENT_ID, SF_CLIENT_SECRET, SF_REFRESH_TOKEN env vars."""
    from mcp_salesforce import SalesforceClient

    return SalesforceClient()


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
    args = parser.parse_args()

    result, logs = run_pipeline(
        mode=args.mode,
        client=_build_client() if args.mode == "real" else None,
    )

    # Validate output
    if not {"risk_score", "alerts", "health_check"}.issubset(result):
        raise ValueError("Pipeline result missing required keys")
    if not 0 <= result["risk_score"] <= 1:
        raise ValueError(f"risk_score out of range: {result['risk_score']}")

    # Write JSON output
    with open(args.log_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Pipeline complete: {args.log_file}")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
