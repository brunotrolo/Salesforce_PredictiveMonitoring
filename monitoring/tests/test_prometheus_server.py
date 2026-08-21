"""Tests for the Prometheus HTTP server."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.request
from http.server import HTTPServer
from pathlib import Path

import pytest

# Ensure monitoring is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prometheus_server import _MetricsHandler


@pytest.fixture
def prom_dir(tmp_path: Path) -> Path:
    """Create a temp directory for .prom files."""
    return tmp_path


@pytest.fixture
def server(prom_dir: Path) -> tuple[HTTPServer, int]:
    """Start a server on a random high port and return (server, port)."""
    server = HTTPServer(("127.0.0.1", 0), _MetricsHandler)
    port = server.server_address[1]
    # Set the module-level PROM_DIR for the handler
    import prometheus_server

    prometheus_server._PROM_DIR = str(prom_dir)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, port
    server.shutdown()


class TestHealthEndpoint:
    def test_health_no_data(self, server: tuple[HTTPServer, int]) -> None:
        _, port = server
        resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/health")
        data = json.loads(resp.read())
        assert data["status"] == "no_data"
        assert resp.status == 200

    def test_health_with_stale_data(
        self, server: tuple[HTTPServer, int], prom_dir: Path
    ) -> None:
        _, port = server
        prom_file = prom_dir / "old.prom"
        prom_file.write_text("monitoring_risk_score 0.5\n")
        # Backdate mtime to 20 minutes ago
        old_time = time.time() - 1200
        os.utime(str(prom_file), (old_time, old_time))
        resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/health")
        data = json.loads(resp.read())
        assert data["status"] == "stale"

    def test_health_with_fresh_data(
        self, server: tuple[HTTPServer, int], prom_dir: Path
    ) -> None:
        _, port = server
        prom_file = prom_dir / "fresh.prom"
        prom_file.write_text("monitoring_risk_score 0.3\n")
        resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/health")
        data = json.loads(resp.read())
        assert data["status"] == "healthy"


class TestMetricsEndpoint:
    def test_returns_503_when_no_data(self, server: tuple[HTTPServer, int]) -> None:
        _, port = server
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics")
            assert False, "Should have raised"
        except urllib.error.HTTPError as exc:
            assert exc.code == 503

    def test_returns_latest_prom(
        self, server: tuple[HTTPServer, int], prom_dir: Path
    ) -> None:
        _, port = server
        old = prom_dir / "2026-01-01.prom"
        old.write_text("monitoring_risk_score 0.1\n")
        # Ensure newer mtime on Windows (1-second granularity)
        time.sleep(1.1)
        new = prom_dir / "2026-01-02.prom"
        new.write_text("monitoring_risk_score 0.9\n")
        resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics")
        body = resp.read().decode()
        assert "monitoring_risk_score 0.9" in body

    def test_returns_valid_prometheus_format(
        self, server: tuple[HTTPServer, int], prom_dir: Path
    ) -> None:
        _, port = server
        prom_file = prom_dir / "valid.prom"
        content = (
            "# HELP monitoring_risk_score Risk score\n"
            "# TYPE monitoring_risk_score gauge\n"
            "monitoring_risk_score 0.42\n"
        )
        prom_file.write_text(content)
        resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics")
        body = resp.read().decode()
        assert "# HELP monitoring_risk_score" in body
        assert "monitoring_risk_score 0.42" in body
        expected_ct = "text/plain; version=0.0.4; charset=utf-8"
        assert resp.headers["Content-Type"] == expected_ct


class Test404:
    def test_unknown_path_returns_404(self, server: tuple[HTTPServer, int]) -> None:
        _, port = server
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/unknown")
            assert False, "Should have raised"
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
