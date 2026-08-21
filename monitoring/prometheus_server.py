"""Prometheus HTTP server — continuous endpoint for scraping.

Stdlib-only HTTP server that serves the latest .prom snapshot file
from the out/ directory on GET /metrics.  Health check at GET /health.

Usage:
    python prometheus_server.py              # default port 9090
    PROM_PORT=9191 python prometheus_server.py

Environment variables:
    PROM_PORT  — HTTP port (default 9090)
    PROM_DIR   — directory to watch for .prom files (default out/)
"""

from __future__ import annotations

import glob
import json
import os
import signal
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

_PROM_DIR = os.environ.get("PROM_DIR", "out")
_PORT = int(os.environ.get("PROM_PORT", "9090"))
_POLL_INTERVAL = 5  # seconds between directory scans
_STALE_THRESHOLD = 600  # consider .prom stale after 10 min


class _MetricsHandler(BaseHTTPRequestHandler):
    """Serve the latest .prom snapshot or health status."""

    server_version = "PrometheusServer/1.0"

    def do_GET(self) -> None:
        if self.path == "/metrics":
            self._serve_metrics()
        elif self.path == "/health":
            self._serve_health()
        else:
            self._send_text(404, '{"error": "not found"}\n', "application/json")

    def _serve_metrics(self) -> None:
        prom_file = self._latest_prom_file()
        if prom_file is None:
            self._send_text(
                503,
                '{"error": "no metrics available yet"}\n',
                "application/json",
            )
            return

        try:
            with open(prom_file, "r", encoding="utf-8") as fh:
                body = fh.read()
        except OSError as exc:
            self._send_text(
                500,
                json.dumps({"error": str(exc)}) + "\n",
                "application/json",
            )
            return

        self._send_text(200, body, "text/plain; version=0.0.4; charset=utf-8")

    def _serve_health(self) -> None:
        prom_file = self._latest_prom_file()
        status = "healthy"
        last_update = None
        if prom_file:
            mtime = os.path.getmtime(prom_file)
            last_update = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
            age = time.time() - mtime
            if age > _STALE_THRESHOLD:
                status = "stale"
        else:
            status = "no_data"

        payload = json.dumps(
            {"status": status, "last_update": last_update, "prom_dir": _PROM_DIR}
        )
        self._send_text(200, payload + "\n", "application/json")

    def _latest_prom_file(self) -> str | None:
        """Find the most recently modified .prom file in _PROM_DIR."""
        pattern = os.path.join(_PROM_DIR, "*.prom")
        files = glob.glob(pattern)
        if not files:
            return None
        return max(files, key=os.path.getmtime)

    def _send_text(
        self, code: int, body: str, content_type: str = "text/plain"
    ) -> None:
        encoded = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt: str, *args: object) -> None:
        """Suppress default stderr logging."""
        pass  # silent — use structured logging if needed


def run_server(port: int = _PORT, prom_dir: str = _PROM_DIR) -> None:
    """Start the HTTP server and block until terminated."""
    global _PROM_DIR
    _PROM_DIR = prom_dir

    server = HTTPServer(("0.0.0.0", port), _MetricsHandler)

    def _shutdown(signum: int, frame: object) -> None:
        server.shutdown()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print(f"Prometheus server listening on :{port}/metrics")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
