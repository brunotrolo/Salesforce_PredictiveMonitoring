"""MCP Salesforce client - Phase 1.

Thin wrapper around the Salesforce Platform MCP server (Streamable HTTP).
No credentials are stored in code: token comes from environment.

Environments:
    SALESFORCE_MCP_URL              MCP server URL (default: sobject-all endpoint)
    SALESFORCE_MCP_TOKEN            OAuth2 bearer token (direct access)
    SALESFORCE_MCP_CLIENT_ID        OAuth2 client id (for refresh flow)
    SALESFORCE_MCP_REFRESH_TOKEN    OAuth2 refresh token (for refresh flow)
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_MCP_URL = "https://api.salesforce.com/platform/mcp/v1/platform/sobject-all"
DEFAULT_PROTOCOL_VERSION = "2025-03-26"
OAUTH_DISCOVERY_URL = (
    "https://api.salesforce.com/.well-known/oauth-authorization-server"
)


class SalesforceClientError(RuntimeError):
    """Raised for MCP protocol, transport or authentication failures."""


class SalesforceClient:
    """Client for the Salesforce Platform MCP server.

    Exposes ``soql_query`` (T3.4 contract) and ``query`` (2-line change alias).
    """

    def __init__(
        self,
        url: str | None = None,
        token: str | None = None,
        client_id: str | None = None,
        refresh_token: str | None = None,
        discovery_url: str | None = None,
    ) -> None:
        self.url = url or os.environ.get("SALESFORCE_MCP_URL", DEFAULT_MCP_URL)
        self.token = token or os.environ.get("SALESFORCE_MCP_TOKEN") or ""
        self.client_id = client_id or os.environ.get("SALESFORCE_MCP_CLIENT_ID") or ""
        self.refresh_token = (
            refresh_token or os.environ.get("SALESFORCE_MCP_REFRESH_TOKEN") or ""
        )
        self.discovery_url = discovery_url or OAUTH_DISCOVERY_URL
        self._session_id: str | None = None

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
            if "401" not in str(exc) or not self._can_refresh():
                raise
            self._refresh_token()
            return self._call_tool(name, arguments)

    # -------------------------------------------------------------- transport

    def _rpc(self, method: str, params: dict[str, Any]) -> Any:
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
            raise SalesforceClientError(
                f"HTTP {exc.code}: {exc.read().decode()[:300]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise SalesforceClientError(f"Transport error: {exc.reason}") from exc

    def _call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
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
        self._rpc("notifications/initialized", {})

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
        """Parse a Streamable HTTP response (JSON or SSE event stream).

        Empty bodies are legal for notifications (204 No Content) and
        return ``None``.
        """
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
        data = urllib.parse.urlencode(
            {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
            }
        ).encode()
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
