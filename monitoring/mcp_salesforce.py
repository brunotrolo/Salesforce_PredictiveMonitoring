"""MCP Salesforce client - Phase 1.

Thin wrapper around the Salesforce Platform MCP server (Streamable HTTP).
No credentials are stored in code: token comes from environment.

The Salesforce Hosted MCP servers require an External Client App (not a
legacy Connected App) with PKCE + JWT-based access tokens enabled and the
scopes ``api``, ``sfap_api`` and ``refresh_token``. Obtain the initial
refresh token with scripts/get_sf_mcp_tokens.py; this client then refreshes
the access token automatically on 401.

Environments:
    SALESFORCE_MCP_URL              MCP server URL (default: sobject-all endpoint)
    SF_CLIENT_ID                    OAuth2 client id (External Client App Consumer Key)
    SF_CLIENT_SECRET                OAuth2 client secret (Consumer Secret)
    SF_REFRESH_TOKEN                OAuth2 refresh token
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from resilience import TokenBucket, is_retryable_error, retry

DEFAULT_MCP_URL = "https://api.salesforce.com/platform/mcp/v1/platform/sobject-all"
DEFAULT_PROTOCOL_VERSION = "2025-03-26"
OAUTH_DISCOVERY_URL = (
    "https://api.salesforce.com/.well-known/oauth-authorization-server"
)


class SalesforceClientError(RuntimeError):
    """Raised for MCP protocol, transport or authentication failures.

    ``code`` mirrors an HTTP status when the failure came from an HTTP
    response (urllib HTTPError shape); ``transient`` marks transport-level
    failures that are safe to retry (429/5xx, connection/timeout). Protocol
    and validation errors are never transient.
    """

    def __init__(
        self, message: str, *, code: int | None = None, transient: bool = False
    ) -> None:
        super().__init__(message)
        self.code = code
        self.transient = transient


class SalesforceClient:
    """Client for the Salesforce Platform MCP server.

    Exposes ``soql_query`` (T3.4 contract) and ``query`` (2-line change alias).
    """

    def __init__(
        self,
        url: str | None = None,
        token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        refresh_token: str | None = None,
        discovery_url: str | None = None,
        *,
        retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        jitter: float = 0.1,
        max_qps: float | None = None,
        bucket_timeout: float = 30.0,
        sleeper: Any = time.sleep,
    ) -> None:
        self.url = url or os.environ.get("SALESFORCE_MCP_URL", DEFAULT_MCP_URL)
        self.token = token or ""
        self.client_id = client_id or os.environ.get("SF_CLIENT_ID") or ""
        self.client_secret = client_secret or os.environ.get("SF_CLIENT_SECRET") or ""
        self.discovery_url = discovery_url or OAUTH_DISCOVERY_URL
        self.refresh_token = refresh_token or os.environ.get("SF_REFRESH_TOKEN") or ""
        self._session_id: str | None = None
        self._retries = retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._jitter = jitter
        self._bucket_timeout = bucket_timeout
        self._sleeper = sleeper
        raw_qps = os.environ.get("SF_MAX_QPS")
        if max_qps is None and raw_qps:
            max_qps = float(raw_qps)
        self.max_qps = max_qps if max_qps and max_qps > 0 else None
        self._bucket: TokenBucket | None = (
            TokenBucket(rate=max_qps, capacity=max_qps, sleeper=sleeper)
            if self.max_qps
            else None
        )

    # ------------------------------------------------------------------ public

    def soql_query(self, soql: str) -> Any:
        """Run a SOQL query via the MCP `soqlQuery` tool (T3.4 contract).

        The Salesforce MCP tool exposes the query as parameter ``q``.
        """
        return self.call_tool("soqlQuery", {"q": soql})

    def query(self, soql: str) -> Any:
        """Alias for ``soql_query`` - the 2-line change from the SPEC."""
        return self.soql_query(soql)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Invoke an MCP tool over Streamable HTTP, refreshing auth on 401."""
        try:
            return self._call_tool(name, arguments)
        except SalesforceClientError as exc:
            # 401 (Unauthorized) is the canonical "access token expired" signal
            # — anything else is a real protocol/transport error and must NOT
            # trigger a token refresh. We compare on the structured code field
            # (set in _rpc_once/_notify's HTTPError handler) rather than on the
            # stringified message: a future log change shouldn't silently break
            # refresh.
            if exc.code != 401 or not self._can_refresh():
                raise
            self._refresh_token()
            return self._call_tool(name, arguments)

    # -------------------------------------------------------------- transport

    def _rpc(self, method: str, params: dict[str, Any]) -> Any:
        """Send one JSON-RPC request with retry on transient transport errors.

        Retries (exponential backoff + jitter) only transient failures:
        HTTP 429/5xx, connection and timeout errors. Protocol errors
        (MCP error responses, invalid JSON, 4xx other than 429) fail fast.
        """
        return retry(
            lambda: self._rpc_once(method, params),
            retries=self._retries,
            base_delay=self._base_delay,
            max_delay=self._max_delay,
            jitter=self._jitter,
            retryable=self._is_retryable_transport,
            sleeper=self._sleeper,
        )

    def _is_retryable_transport(self, exc: BaseException) -> bool:
        """True when the failure came from the transport, not the protocol."""
        return is_retryable_error(exc) or (
            isinstance(exc, SalesforceClientError) and exc.transient
        )

    def _rpc_once(self, method: str, params: dict[str, Any]) -> Any:
        """Send one JSON-RPC request; returns the result (parsed JSON or SSE)."""
        payload = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        ).encode()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        request = urllib.request.Request(
            self.url, data=payload, method="POST", headers=headers
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                session_id = response.headers.get("Mcp-Session-Id")
                if session_id:
                    self._session_id = session_id
                body = response.read().decode()
                message = self._parse_response(
                    body, response.headers.get_content_type()
                )
                return self._unwrap_rpc(message)
            raise AssertionError("unreachable")
        except urllib.error.HTTPError as exc:
            code = exc.code
            raise SalesforceClientError(
                f"HTTP {code}: {exc.read().decode()[:300]}",
                code=code,
                transient=code == 429 or 500 <= code <= 599,
            ) from exc
        except urllib.error.URLError as exc:
            raise SalesforceClientError(
                f"Transport error: {exc.reason}", transient=True
            ) from exc

    def _call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if self._bucket is not None and not self._bucket.acquire(
            block=True, timeout=self._bucket_timeout
        ):
            raise SalesforceClientError(
                f"Rate limit: SF_MAX_QPS={self.max_qps} exhausted after "
                f"{self._bucket_timeout}s wait"
            )
        if self._session_id is None:
            self._initialize()
        result = self._rpc("tools/call", {"name": name, "arguments": arguments})
        if isinstance(result, dict) and result.get("isError"):
            raise SalesforceClientError(
                f"MCP tool '{name}' failed: {result.get('content')}"
            )
        return self._extract_content(result)

    def _initialize(self) -> None:
        result = self._rpc(
            "initialize",
            {
                "protocolVersion": DEFAULT_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "salesforce-predictive-monitoring",
                    "version": "1.0",
                },
            },
        )
        if not isinstance(result, dict) or "capabilities" not in result:
            raise SalesforceClientError(f"Unexpected initialize response: {result}")
        self._notify("notifications/initialized", {})

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        """Send a JSON-RPC notification (no id); the server replies 202/204."""
        payload = json.dumps(
            {"jsonrpc": "2.0", "method": method, "params": params}
        ).encode()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        request = urllib.request.Request(
            self.url, data=payload, method="POST", headers=headers
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                session_id = response.headers.get("Mcp-Session-Id")
                if session_id:
                    self._session_id = session_id
                body = response.read().decode()
                message = self._parse_response(
                    body, response.headers.get_content_type()
                )
                if isinstance(message, dict) and "error" in message:
                    raise SalesforceClientError(
                        f"MCP error: {message['error'].get('code')}: "
                        f"{message['error'].get('message')}"
                    )
        except urllib.error.HTTPError as exc:
            raise SalesforceClientError(
                f"HTTP {exc.code}: {exc.read().decode()[:300]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise SalesforceClientError(f"Transport error: {exc.reason}") from exc

    # ------------------------------------------------------------------ parse

    @staticmethod
    def _unwrap_rpc(message: Any) -> Any:
        """Unwrap a JSON-RPC response envelope (result or error)."""
        if not isinstance(message, dict):
            return message
        if "error" in message:
            error = message["error"]
            raise SalesforceClientError(
                f"MCP error: {error.get('code')}: {error.get('message')}"
            )
        return message.get("result", message)

    @staticmethod
    def _parse_response(body: str, content_type: str | None) -> Any:
        """Parse a Streamable HTTP response (JSON or SSE event stream)."""
        if not body or not body.strip():
            return None
        try:
            if content_type and "text/event-stream" in content_type:
                for line in body.splitlines():
                    if line.startswith("data:"):
                        return json.loads(line[5:].strip())
                raise SalesforceClientError("Empty SSE event stream")
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise SalesforceClientError(
                f"Invalid JSON response: {exc.msg} at {exc.pos}: {body[:200]!r}"
            ) from exc

    @staticmethod
    def _extract_content(result: Any) -> Any:
        """Extract the text payload from an MCP tools/call result."""
        if not isinstance(result, dict):
            return result
        content = result.get("content", [])
        if isinstance(content, list):
            texts = [
                item.get("text")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            if texts:
                return texts[0]
        return result

    # ------------------------------------------------------------------ auth

    def _can_refresh(self) -> bool:
        return bool(self.client_id and self.refresh_token)

    def _refresh_token(self) -> None:
        """Refresh the OAuth2 token via the discovery document token endpoint."""
        token_endpoint = self._discover_token_endpoint()
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        data = urllib.parse.urlencode(payload).encode()
        request = urllib.request.Request(
            token_endpoint,
            data=data,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            raise SalesforceClientError(
                f"Token refresh failed: HTTP {exc.code}: {exc.read().decode()[:300]}"
            ) from exc
        access_token = body.get("access_token")
        if not access_token:
            raise SalesforceClientError(
                f"Token refresh failed: no access_token in response: {body}"
            )
        self.token = access_token
        new_refresh = body.get("refresh_token")
        if new_refresh and new_refresh != self.refresh_token:
            self.refresh_token = new_refresh

    def _discover_token_endpoint(self) -> str:
        request = urllib.request.Request(
            self.discovery_url, method="GET", headers={"Accept": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                metadata = json.loads(response.read().decode())
        except urllib.error.URLError as exc:
            raise SalesforceClientError(
                f"OAuth discovery failed: {exc.reason}"
            ) from exc
        token_endpoint = metadata.get("token_endpoint")
        if not token_endpoint:
            raise SalesforceClientError(
                f"OAuth discovery: no token_endpoint in {metadata}"
            )
        return token_endpoint
