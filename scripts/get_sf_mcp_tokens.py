#!/usr/bin/env python3
"""Get OAuth2 tokens for the Salesforce Hosted MCP servers (Phase 1, auth).

The Salesforce Hosted MCP servers (api.salesforce.com/platform/mcp/v1/<server>)
require an External Client App (not a legacy Connected App) configured with:

  * OAuth scopes: ``api``, ``sfap_api``, ``refresh_token``
  * Require Proof Key for Code Exchange (PKCE): enabled
  * Issue JSON Web Token (JWT)-based access tokens for named users: enabled

This script runs the authorization-code + PKCE flow once, opens the browser,
captures the redirect on localhost, exchanges the code for tokens and prints
the refresh token (the access token is never printed; it expires in ~2h and
the pipeline refreshes it automatically via grant_type=refresh_token).

Usage:
    python get_sf_mcp_tokens.py <client_id> <client_secret>

Store the printed refresh token as the GitHub secret SF_REFRESH_TOKEN
(``gh secret set SF_REFRESH_TOKEN``). Also update SF_CLIENT_ID and
SF_CLIENT_SECRET with the External Client App's Consumer Key / Secret.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.server
import json
import secrets
import sys
import urllib.parse
import urllib.request
import webbrowser

AUTHORIZE_URL = "https://login.salesforce.com/services/oauth2/authorize"
TOKEN_URL = "https://login.salesforce.com/services/oauth2/token"
REDIRECT_PORT = 8899
REDIRECT_URI = f"http://127.0.0.1:{REDIRECT_PORT}/callback"
SCOPES = "api sfap_api refresh_token"


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    """Captures the ?code=...&state=... redirect from the browser."""

    captured = {}

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/callback" and "code" in params:
            CallbackHandler.captured = {
                "code": params["code"][0],
                "state": params.get("state", [""])[0],
            }
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h2>Autorizado.</h2>"
                b"<p>Voce pode fechar esta aba.</p></body></html>"
            )
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args: object) -> None:
        pass


def _pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def _exchange_code(
    client_id: str, client_secret: str, code: str, verifier: str
) -> dict:
    payload = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
            "code_verifier": verifier,
        }
    ).encode()
    request = urllib.request.Request(
        TOKEN_URL,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        raise SystemExit(
            f"Token exchange failed: HTTP {exc.code}: {body[:400]}"
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("client_id", help="Consumer Key da External Client App")
    parser.add_argument("client_secret", help="Consumer Secret da External Client App")
    args = parser.parse_args()

    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(16)
    params = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": args.client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "prompt": "consent",
        }
    )

    server = http.server.HTTPServer(("127.0.0.1", REDIRECT_PORT), CallbackHandler)
    print("Abra a URL a seguir no navegador e aprove o acesso:")
    print(f"  {AUTHORIZE_URL}?{params}")
    webbrowser.open(f"{AUTHORIZE_URL}?{params}")
    server.handle_request()
    server.server_close()

    captured = CallbackHandler.captured
    if not captured or captured.get("state") != state:
        raise SystemExit("Falha: callback sem code ou state invalido.")
    print("Code recebido. Trocando por tokens...")

    tokens = _exchange_code(
        args.client_id, args.client_secret, captured["code"], verifier
    )
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise SystemExit(f"Falha: sem refresh_token na resposta: {tokens}")

    print("\n=== Tokens obtidos ===")
    print(f"instance_url: {tokens.get('instance_url', 'N/A')}")
    print(f"scope: {tokens.get('scope', 'N/A')}")
    print(f"access_token (nao compartilhe, expira em ~2h): "
          f"{tokens['access_token'][:12]}...")
    print("\nGrave o refresh token abaixo como secret (copie a linha inteira):")
    print(f"SF_REFRESH_TOKEN = {refresh_token}")
    print("\nDepois rode:")
    print("  gh secret set SF_REFRESH_TOKEN <<< '<o refresh token acima>'")
    print(f"  gh secret set SF_CLIENT_ID <<< '{args.client_id}'")
    print("  gh secret set SF_CLIENT_SECRET <<< '<o consumer secret>'")
    print("\nE dispare o collect:")
    print("  gh workflow run collect.yml")


if __name__ == "__main__":
    sys.exit(main())