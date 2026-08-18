#!/usr/bin/env python3
"""Get OAuth2 tokens for the Salesforce Hosted MCP servers (bootstrap).

The Salesforce Hosted MCP servers (api.salesforce.com/platform/mcp/v1/<server>)
require an External Client App (not a legacy Connected App) configured with:

  * OAuth scopes: ``api``, ``sfap_api``, ``refresh_token`` (e ``mcp_api``)
  * Require Proof Key for Code Exchange (PKCE): enabled
  * Issue JSON Web Token (JWT)-based access tokens for named users: enabled

External Client Apps do not accept plain-HTTP redirect URIs, so this script
uses Salesforce's own success callback (https://login.salesforce.com/
services/oauth2/success) and a manual copy-paste of the ``code``: it opens
the authorization URL in the browser, you approve, the browser lands on the
success page whose URL contains ``?code=...``, and you paste that URL (or
just the code) back into the terminal.

The access token is never printed; the pipeline refreshes it automatically
via grant_type=refresh_token (and captures the rotated refresh token).

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
import json
import re
import secrets
import sys
import urllib.parse
import urllib.request
import webbrowser

AUTHORIZE_URL = "https://login.salesforce.com/services/oauth2/authorize"
TOKEN_URL = "https://login.salesforce.com/services/oauth2/token"
REDIRECT_URI = "https://login.salesforce.com/services/oauth2/success"
SCOPES = "api sfap_api mcp_api refresh_token"


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
    url = f"{AUTHORIZE_URL}?{params}"
    print("Abra a URL a seguir no navegador, aprove o acesso e espere a")
    print("pagina de sucesso do Salesforce carregar:")
    print(f"  {url}")
    print(f"state esperado: {state}")
    webbrowser.open(url)

    pasted = input("\nCole aqui a URL final do navegador (ou so o code): ").strip()
    code_match = re.search(r"[?&#]code=([^&#]+)", pasted)
    state_match = re.search(r"[?&#]state=([^&#]+)", pasted)
    if not code_match:
        raise SystemExit("Falha: nao encontrei o parametro code na entrada.")
    code = urllib.parse.unquote(code_match.group(1))
    if state_match and urllib.parse.unquote(state_match.group(1)) != state:
        raise SystemExit("Falha: state nao confere (possivel CSRF).")
    print("Code recebido. Trocando por tokens...")

    tokens = _exchange_code(args.client_id, args.client_secret, code, verifier)
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise SystemExit(f"Falha: sem refresh_token na resposta: {tokens}")

    print("\n=== Tokens obtidos ===")
    print(f"instance_url: {tokens.get('instance_url', 'N/A')}")
    print(f"scope: {tokens.get('scope', 'N/A')}")
    print(
        f"access_token (nao compartilhe, expira em ~2h): "
        f"{tokens['access_token'][:12]}..."
    )
    print("\nGrave o refresh token abaixo como secret (copie a linha inteira):")
    print(f"SF_REFRESH_TOKEN = {refresh_token}")
    print("\nDepois rode:")
    print("  gh secret set SF_REFRESH_TOKEN <<< '<o refresh token acima>'")
    print("  gh secret set SF_CLIENT_ID <<< '<o consumer key>'")
    print("  gh secret set SF_CLIENT_SECRET <<< '<o consumer secret>'")
    print("\nE dispare o collect:")
    print("  gh workflow run collect.yml")


if __name__ == "__main__":
    sys.exit(main())