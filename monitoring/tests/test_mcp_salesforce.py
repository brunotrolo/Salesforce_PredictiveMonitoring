"""Tests for mcp_salesforce.SalesforceClient against a local mock MCP server."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

import pytest
from mcp_salesforce import SalesforceClient, SalesforceClientError
from resilience import RetryExhausted


class FakeSleeper:
    """Records sleep durations so tests never actually wait."""

    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


class MockMCPServer:
    """Minimal Streamable HTTP MCP server for tests.

    Modes:
        - "ok": initialize + tools/call -> soqlQuery returns records
        - "sse": same, but tools/call answered as text/event-stream
        - "unauthorized_once": first authorized request returns 401, then ok
        - "unauthorized_always": always 401 (no refresh path)
        - "flaky500": first ``fail_until`` tools/call return 500, then ok
        - "flaky400": first ``fail_until`` tools/call return 400, then ok
        - "broken": invalid JSON / unexpected initialize response
    """

    def __init__(self, mode: str = "ok", fail_until: int = 0) -> None:
        self.mode = mode
        self.fail_until = fail_until
        self.tools_calls = 0
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
                    if server.mode in ("flaky500", "flaky400"):
                        server.tools_calls += 1
                        if server.tools_calls <= server.fail_until:
                            self._json(
                                500 if server.mode == "flaky500" else 400,
                                {"error": "injected failure"},
                            )
                            return
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
    """Serves POST /token for the refresh flow.

    ``rotate=True`` emulates Salesforce behaviour: each refresh returns a
    NEW refresh token and the previous one stops working.
    """

    def __init__(self, rotate: bool = False) -> None:
        self.refreshed = 0
        self.rotate = rotate
        self.issued_tokens: list[str] = []

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
                length = int(self.headers.get("Content-Length", 0))
                body = parse_qs(self.rfile.read(length).decode())
                if token.rotate:
                    used = (body.get("refresh_token") or [""])[0]
                    if token.issued_tokens and used != token.issued_tokens[-1]:
                        self.send_response(400)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(
                            json.dumps(
                                {
                                    "error": "invalid_grant",
                                    "error_description": "expired access/refresh token",
                                }
                            ).encode()
                        )
                        return
                    new_rt = f"rotated-rt-{token.refreshed}"
                    token.issued_tokens.append(new_rt)
                    payload = {
                        "access_token": f"fresh-token-{token.refreshed}",
                        "refresh_token": new_rt,
                    }
                else:
                    payload = {"access_token": "fresh-token-abc"}
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(payload).encode())

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

    def test_rotated_refresh_token_is_updated_in_memory(self, mock_server_401_once):
        """Salesforce rotates the refresh token: the new one must be stored
        in memory for the current session."""
        server, url = mock_server_401_once
        token_endpoint = MockTokenEndpoint(rotate=True)
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
            assert client.refresh_token == "rotated-rt-1"
        finally:
            token_endpoint.stop()

    def test_refresh_token_from_env(self, monkeypatch):
        """SF_REFRESH_TOKEN env var is picked up by the client."""
        monkeypatch.setenv("SF_REFRESH_TOKEN", "env-rt-123")
        client = SalesforceClient(client_id="c1")
        assert client.refresh_token == "env-rt-123"

    def test_401_detection_uses_code_not_string(self):
        """call_tool must trigger refresh based on the structured HTTP code,
        not on the stringified message — a future copy change in the error
        text must not silently disable token rotation.
        """
        server = MockMCPServer("unauthorized_once")
        url = server.start()
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
            # Sanity: code-based detection triggers refresh and the call succeeds
            result = client.soql_query("SELECT Id FROM Log__c")
            assert json.loads(result)["totalSize"] == 1
            assert token_endpoint.refreshed == 1
            assert client.token == "fresh-token-abc"
        finally:
            server.stop()
            token_endpoint.stop()

    def test_non_401_error_does_not_trigger_refresh(self):
        """A 500/400 from the MCP server is a protocol/transport error and
        must NOT trigger a token refresh — only 401 means "token expired".
        """
        server = MockMCPServer("flaky500", fail_until=10**9)
        url = server.start()
        token_endpoint = MockTokenEndpoint()
        token_endpoint.start()
        server._token_endpoint_url = f"http://127.0.0.1:{token_endpoint.port}/token"
        try:
            client = SalesforceClient(
                url=url,
                token="tok-1",
                client_id="client-1",
                refresh_token="refresh-1",
                retries=2,
                sleeper=lambda _: None,
                discovery_url=f"{url}/.well-known/oauth-authorization-server",
            )
            with pytest.raises(RetryExhausted):
                client.soql_query("SELECT Id FROM Log__c")
            # Token endpoint was never contacted — refresh is reserved for 401
            assert token_endpoint.refreshed == 0
        finally:
            server.stop()
            token_endpoint.stop()

    def test_client_secret_is_sent_in_refresh(self, mock_server_401_once):
        """client_secret is included in the refresh request."""
        server, url = mock_server_401_once
        token_endpoint = MockTokenEndpoint()
        token_endpoint.start()
        server._token_endpoint_url = f"http://127.0.0.1:{token_endpoint.port}/token"
        try:
            client = SalesforceClient(
                url=url,
                token="tok-expired",
                client_id="client-1",
                client_secret="secret-1",
                refresh_token="refresh-1",
                discovery_url=f"{url}/.well-known/oauth-authorization-server",
            )
            result = client.soql_query("SELECT Id FROM Log__c")
            assert json.loads(result)["totalSize"] == 1
            assert token_endpoint.refreshed == 1
        finally:
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

    def test_transport_error_is_retried_then_exhausted(self):
        client = SalesforceClient(
            url="http://127.0.0.1:1", token="tok-1", retries=2, sleeper=lambda _: None
        )
        with pytest.raises(RetryExhausted):
            client.soql_query("SELECT Id FROM Log__c")

    def test_url_from_environment(self, mock_server, monkeypatch):
        server, url = mock_server
        monkeypatch.setenv("SALESFORCE_MCP_URL", url)
        client = SalesforceClient()
        assert client.url == url


class TestRetryAndRateLimit:
    def test_retries_transient_500_and_succeeds(self):
        server = MockMCPServer("flaky500", fail_until=2)
        url = server.start()
        try:
            sleeper = FakeSleeper()
            client = SalesforceClient(
                url=url, token="tok-1", retries=3, jitter=0.0, sleeper=sleeper
            )
            result = client.soql_query("SELECT Id FROM Log__c")
            assert json.loads(result)["totalSize"] == 1
            assert server.tools_calls == 3
            assert sleeper.calls == [1.0, 2.0]
        finally:
            server.stop()

    def test_500_exhausted_raises_retry_exhausted(self):
        server = MockMCPServer("flaky500", fail_until=10**9)
        url = server.start()
        try:
            client = SalesforceClient(
                url=url, token="tok-1", retries=2, jitter=0.0, sleeper=lambda _: None
            )
            with pytest.raises(RetryExhausted):
                client.soql_query("SELECT Id FROM Log__c")
            assert server.tools_calls == 3
        finally:
            server.stop()

    def test_400_fails_fast_without_retry(self):
        server = MockMCPServer("flaky400", fail_until=10**9)
        url = server.start()
        try:
            client = SalesforceClient(
                url=url, token="tok-1", retries=3, sleeper=lambda _: None
            )
            with pytest.raises(SalesforceClientError, match="HTTP 400") as exc_info:
                client.soql_query("SELECT Id FROM Log__c")
            assert exc_info.value.code == 400
            assert not exc_info.value.transient
            assert server.tools_calls == 1
        finally:
            server.stop()

    def test_mcp_protocol_error_is_not_retried(self):
        server = MockMCPServer("broken")
        url = server.start()
        try:
            client = SalesforceClient(
                url=url, token="tok-1", retries=3, sleeper=lambda _: None
            )
            with pytest.raises(SalesforceClientError):
                client.soql_query("SELECT Id FROM Log__c")
            assert len(server.calls) == 1
        finally:
            server.stop()

    def test_transport_error_backs_off_between_attempts(self):
        sleeper = FakeSleeper()
        client = SalesforceClient(
            url="http://127.0.0.1:1",
            token="tok-1",
            retries=2,
            jitter=0.0,
            sleeper=sleeper,
        )
        with pytest.raises(RetryExhausted):
            client.soql_query("SELECT Id FROM Log__c")
        assert sleeper.calls == [1.0, 2.0]

    def test_rate_limit_exhausted_raises_without_calling_server(self):
        server = MockMCPServer("ok")
        url = server.start()
        try:
            client = SalesforceClient(
                url=url, token="tok-1", max_qps=1e-9, bucket_timeout=0.02
            )
            with pytest.raises(SalesforceClientError, match="Rate limit"):
                client.soql_query("SELECT Id FROM Log__c")
            assert server.calls == []
        finally:
            server.stop()

    def test_rate_limit_allows_within_qps(self):
        server = MockMCPServer("ok")
        url = server.start()
        try:
            client = SalesforceClient(url=url, token="tok-1", max_qps=100.0)
            result = client.soql_query("SELECT Id FROM Log__c")
            assert json.loads(result)["totalSize"] == 1
        finally:
            server.stop()

    def test_max_qps_from_env(self, monkeypatch):
        monkeypatch.setenv("SF_MAX_QPS", "2.5")
        client = SalesforceClient()
        assert client.max_qps == 2.5
        assert client._bucket is not None

    def test_no_bucket_without_max_qps(self):
        assert SalesforceClient()._bucket is None

    def test_transient_classification(self):
        client = SalesforceClient()
        assert client._is_retryable_transport(
            SalesforceClientError("t", transient=True)
        )
        assert client._is_retryable_transport(SalesforceClientError("x", code=503))
        assert not client._is_retryable_transport(SalesforceClientError("p"))
        assert not client._is_retryable_transport(SalesforceClientError("a", code=401))
