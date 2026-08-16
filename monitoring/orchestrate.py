#!/usr/bin/env python
"""Monitoring pipeline orchestrator - Phase 0 (Mock mode)."""
from __future__ import annotations

import sys
import os
import json
import argparse
from datetime import datetime, timezone

# Ensure services are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "collector", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "heuristic", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "comparison", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "shared", "src"))


def generate_mock_logs() -> list[dict]:
    """Generate mock Salesforce logs for testing."""
    now = datetime.now(timezone.utc).isoformat()
    return [
        {"log_id": "L1", "status_code": 200, "duration_ms": 100, "timestamp": now, "org_id": "ORG-MOCK", "resource": "/api/accounts"},
        {"log_id": "L2", "status_code": 500, "duration_ms": 1500, "timestamp": now, "org_id": "ORG-MOCK", "resource": "/api/users"},
        {"log_id": "L3", "status_code": 200, "duration_ms": 200, "timestamp": now, "org_id": "ORG-MOCK", "resource": "/api/products"},
    ]


def run_pipeline() -> tuple[dict, list[dict]]:
    """Run the full mock monitoring pipeline: collector -> heuristic -> comparison."""
    from collector import LogCollector
    from heuristic import HeuristicEngine
    from comparison import ComparisonService

    # Step 1: Collect
    collector = LogCollector()
    raw_logs = generate_mock_logs()
    logs = collector.load(raw_logs)
    validation = collector.validate(raw_logs)

    # Step 2: Analyze
    engine = HeuristicEngine()
    analysis = engine.analyze([l.model_dump() if hasattr(l, 'model_dump') else l.__dict__ for l in logs])

    # Step 3: Compare
    comparator = ComparisonService()
    comparison = comparator.compare(analysis)

    # Build result
    now = datetime.now(timezone.utc).isoformat()
    result = {
        "timestamp": now,
        "risk_score": analysis["risk_score"],
        "errors_count": analysis["errors_count"],
        "slow_requests_count": analysis["slow_count"],
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Salesforce Predictive Monitoring Pipeline")
    parser.add_argument("--mode", default="mock", choices=["mock"], help="Run mode (Fase 0: only mock)")
    parser.add_argument("--log-file", default="monitoring_output.json", help="Output JSON file path")
    args = parser.parse_args()

    if args.mode != "mock":
        print("ERROR: Only mock mode supported in Fase 0")
        sys.exit(1)

    result, logs = run_pipeline()

    # Validate output
    assert "risk_score" in result
    assert "alerts" in result
    assert "health_check" in result
    assert 0 <= result["risk_score"] <= 1

    # Write JSON output
    with open(args.log_file, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Pipeline complete: {args.log_file}")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
