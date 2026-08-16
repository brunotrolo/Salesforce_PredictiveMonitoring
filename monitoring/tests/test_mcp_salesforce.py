"""Tests for mcp_salesforce.SalesforceClient against a local mock MCP server."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from mcp_salesforce import SalesforceClient, SalesforceClientError


class MockMCPServer:
    """Minimal Streamable HTTP MCP server for tests.

    Modes:
        - "ok": initialize + tools/call -> soqlQuery returns records
        - "sse": same, but tools/call answered as text/event-stream
        - "unauthorized_once": first authorized request returns 401, then ok
        - "unauthorized_always": always 401 (no refresh path)
        - "broken": invalid JSON / unexpected initialize response
    """

    def __init__(self, mode: str = "ok") -> None:
        self.mode = mode
        self.calls: list[dict] = []
        self.sessions: list[str | None] = []
        self.authorized_requests = 0
        self._token_endpoint_url: str | None = None

    def start(self) -> str:
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), self._handler_factory())
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.httpd.server_address
        return f"http://{host}:{port}"

    def stop(self) -> None:
        self.httpd.shutdown()

    def _handler_factory(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length).decode())
                server.calls.append(
                    {
                        "path": self.path,
                        "method": body.get("method"),
                        "id": body.get("id"),
                    }
                )
                server.sessions.append(self.headers.get("Mcp-Session-Id"))

                if server.mode == "broken":
                    self._json(200, b"not json")
                    return

                if body.get("method") == "initialize":
                    self.send_response(200)
                    self.send_header("Mcp-Session-Id", "sess-123")
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(
                        json.dumps(
                            {
                                "jsonrpc": "2.0",
                                "id": body.get("id"),
                                "result": {
                                    "protocolVersion": "2025-03-26",
                                    "capabilities": {"tools": {}},
                                    "serverInfo": {"name": "mock", "version": "1"},
                                },
                            }
                        ).encode()
                    )
                    return

                if body.get("method") == "notifications/initialized":
                    if server.mode == "empty_notification":
                        self.send_response(204)
                        self.end_headers()
                        return
                    self._json(200, {})
                    return

                if body.get("method") == "tools/call":
                    if (
                        server.mode == "unauthorized_once"
                        and server.authorized_requests == 0
                    ):
                        server.authorized_requests += 1
                        self._json(401, {"errors": [{"message": "Invalid token"}]})
                        return
                    if server.mode == "unauthorized_always":
                        self._json(401, {"errors": [{"message": "Invalid token"}]})
                        return
                    result = {
                        "jsonrpc": "2.0",
                        "id": body.get("id"),
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(
                                        {
                                            "totalSize": 1,
                                            "records": [
                                                {"Id": "a00x0000001", "Name": "Log 1"}
                                            ],
                                        }
                                    ),
                                }
                            ],
                            "isError": False,
                        },
                    }
                    if server.mode == "sse":
                        self.send_response(200)
                        self.send_header("Content-Type", "text/event-stream")
                        self.end_headers()
                        self.wfile.write(
                            f"event: message\ndata: {json.dumps(result)}\n\n".encode()
                        )
                        return
                    self._json(200, result)
                    return

                self._json(404, {"error": "unknown method"})

            def do_GET(self):
                if self.path.endswith("/.well-known/oauth-authorization-server"):
                    self._json(
                        200,
                        {
                            "token_endpoint": server._token_endpoint_url
                            or server._token_endpoint
                        },
                    )
                    return
                self._json(404, {"error": "not found"})

            def _json(self, code: int, payload) -> None:
                body = (
                    json.dumps(payload).encode()
                    if not isinstance(payload, bytes)
                    else payload
                )
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args) -> None:  # silence
                pass

        return Handler

    @property
    def _token_endpoint(self) -> str:
        if self._token_endpoint_url:
            return self._token_endpoint_url
        return f"http://127.0.0.1:{self.httpd.server_address[1]}/token"


class MockTokenEndpoint:
    """Serves POST /token for the refresh flow."""

    def __init__(self) -> None:
        self.refreshed = 0

    def start(self) -> None:
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), self._handler_factory())
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.httpd.server_address[1]

    def stop(self) -> None:
        self.httpd.shutdown()

    def _handler_factory(self):
        token = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                token.refreshed += 1
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(
                    json.dumps({"access_token": "fresh-token-abc"}).encode()
                )

            def log_message(self, *args) -> None:  # silence
                pass

        return Handler


@pytest.fixture
def mock_server():
    server = MockMCPServer("ok")
    url = server.start()
    yield server, url
    server.stop()


@pytest.fixture
def mock_server_401_once():
    server = MockMCPServer("unauthorized_once")
    url = server.start()
    yield server, url
    server.stop()


class TestSoqlQuery:
    def test_returns_records_from_tools_call(self, mock_server):
        server, url = mock_server
        client = SalesforceClient(url=url, token="tok-1")
        result = client.soql_query("SELECT Id FROM Log__c LIMIT 1")
        assert result is not None
        parsed = json.loads(result)
        assert parsed["totalSize"] == 1
        assert parsed["records"][0]["Id"] == "a00x0000001"

    def test_query_alias_matches_soql_query(self, mock_server):
        server, url = mock_server
        client = SalesforceClient(url=url, token="tok-1")
        assert client.query("SELECT Id FROM Log__c") == client.soql_query(
            "SELECT Id FROM Log__c"
        )

    def test_initializes_session_before_tool_call(self, mock_server):
        server, url = mock_server
        client = SalesforceClient(url=url, token="tok-1")
        client.soql_query("SELECT Id FROM Log__c")
        methods = [c["method"] for c in server.calls]
        assert methods == ["initialize", "notifications/initialized", "tools/call"]
        assert "sess-123" in server.sessions[2:]

    def test_notifications_initialized_is_sent_without_id(self, mock_server):
        server, url = mock_server
        client = SalesforceClient(url=url, token="tok-1")
        client.soql_query("SELECT Id FROM Log__c")
        notify_call = next(
            c for c in server.calls if c["method"] == "notifications/initialized"
        )
        assert notify_call["id"] is None

    def test_parses_sse_response(self):
        server = MockMCPServer("sse")
        url = server.start()
        try:
            client = SalesforceClient(url=url, token="tok-1")
            result = client.soql_query("SELECT Id FROM Log__c")
            assert json.loads(result)["totalSize"] == 1
        finally:
            server.stop()

    def test_empty_notification_response_is_silently_accepted(self):
        server = MockMCPServer("empty_notification")
        url = server.start()
        try:
            client = SalesforceClient(url=url, token="tok-1")
            result = client.soql_query("SELECT Id FROM Log__c")
            assert json.loads(result)["totalSize"] == 1
        finally:
            server.stop()


class TestAuth:
    def test_401_without_refresh_credentials_raises(self, mock_server_401_once):
        server, url = mock_server_401_once
        client = SalesforceClient(url=url, token="tok-expired")
        with pytest.raises(SalesforceClientError, match="401"):
            client.soql_query("SELECT Id FROM Log__c")

    def test_401_triggers_refresh_and_retries(self, mock_server_401_once):
        server, url = mock_server_401_once
        token_endpoint = MockTokenEndpoint()
        token_endpoint.start()
        server._token_endpoint_url = f"http://127.0.0.1:{token_endpoint.port}/token"
        try:
            client = SalesforceClient(
                url=url,
                token="tok-expired",
                client_id="client-1",
                refresh_token="refresh-1",
                discovery_url=f"{url}/.well-known/oauth-authorization-server",
            )
            result = client.soql_query("SELECT Id FROM Log__c")
            assert json.loads(result)["totalSize"] == 1
            assert token_endpoint.refreshed == 1
            assert client.token == "fresh-token-abc"
        finally:
            token_endpoint.stop()

    def test_refresh_then_401_again_raises(self):
        server = MockMCPServer("unauthorized_always")
        url = server.start()
        token_endpoint = MockTokenEndpoint()
        token_endpoint.start()
        server._token_endpoint_url = f"http://127.0.0.1:{token_endpoint.port}/token"
        try:
            client = SalesforceClient(
                url=url,
                token="tok",
                client_id="c",
                refresh_token="r",
                discovery_url=f"{url}/.well-known/oauth-authorization-server",
            )
            with pytest.raises(SalesforceClientError, match="401"):
                client.soql_query("SELECT Id FROM Log__c")
        finally:
            server.stop()
            token_endpoint.stop()


class TestErrors:
    def test_broken_server_response_raises(self):
        server = MockMCPServer("broken")
        url = server.start()
        try:
            client = SalesforceClient(url=url, token="tok-1")
            with pytest.raises(SalesforceClientError):
                client.soql_query("SELECT Id FROM Log__c")
        finally:
            server.stop()

    def test_transport_error_raises(self):
        client = SalesforceClient(url="http://127.0.0.1:1", token="tok-1")
        with pytest.raises(SalesforceClientError):
            client.soql_query("SELECT Id FROM Log__c")

    def test_token_from_environment(self, mock_server, monkeypatch):
        server, url = mock_server
        monkeypatch.setenv("SALESFORCE_MCP_URL", url)
        monkeypatch.setenv("SALESFORCE_MCP_TOKEN", "env-tok")
        client = SalesforceClient()
        assert client.token == "env-tok"
        assert client.url == url
