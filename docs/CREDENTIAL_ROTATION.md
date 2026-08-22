# Credential Rotation — Salesforce Predictive Monitoring

The pipeline depends on three external identities, each with its own secret
and its own lifetime. Rotate them periodically (recommended every 90 days)
or immediately after any suspected exposure (paste in chat, leaked log,
contractor offboarding, etc.).

This doc covers the manual steps an admin must perform in the **Salesforce
Setup UI** and the **GitHub UI** — they cannot be scripted from the
pipeline itself.

---

## 1. Salesforce External Client App (PKCE + JWT)

The MCP endpoint at `api.salesforce.com/platform/mcp/v1/...` requires an
**External Client App** (not the legacy Connected App type). This app
issues JWT-based access tokens and supports Refresh Token Rotation.

### When to rotate

- 90 days since the last rotation
- Suspected credential exposure
- Org security policy mandates it
- Consumer Key / Consumer Secret need to be invalidated

### Procedure

1. **Salesforce Setup → External Client Apps Manager** → open the app
   used by `SF_CLIENT_ID` (in this org: the one whose Consumer Key
   matches `gh secret get SF_CLIENT_ID`).
2. **Regenerate Consumer Secret** (top right of the app detail page).
   This invalidates the existing `SF_CLIENT_SECRET` and forces a new
   `gh secret set SF_CLIENT_SECRET`.
3. **Rotate the refresh token** by re-running the PKCE bootstrap with
   the **new** Consumer Key/Secret:
   ```bash
   python scripts/get_sf_mcp_tokens.py \
       "<NEW_CONSUMER_KEY>" \
       "<NEW_CONSUMER_SECRET>"
   ```
   Approve in browser, paste the callback URL. The script prints the
   new `SF_REFRESH_TOKEN`.
4. **Update the three GitHub secrets**:
   ```bash
   gh secret set SF_CLIENT_ID      <<< '<NEW_CONSUMER_KEY>'
   gh secret set SF_CLIENT_SECRET  <<< '<NEW_CONSUMER_SECRET>'
   gh secret set SF_REFRESH_TOKEN  <<< '<NEW_REFRESH_TOKEN>'
   ```
5. **Validate**: `gh workflow run collect.yml` — first run should be
   green; check `gh secret list` and confirm `SF_REFRESH_TOKEN` rotated.

### What does NOT need to happen

- Re-create the External Client App — regenerating the Secret is enough.
- Re-install the package in the org — not applicable for ECA.
- Update anything in the SF org's user permissions — already granted.

---

## 2. GitHub App private key

The `actions/create-github-app-token@v1` action mints a 1-hour
installation token from a long-lived private key. The key is stored in
the `APP_PRIVATE_KEY` secret.

### When to rotate

- 90 days since the last rotation (GitHub recommends; no hard expiry)
- Suspected exposure of the `.pem` file
- GitHub sends a security alert about the App

### Procedure

1. **GitHub → Settings → Developer settings → GitHub Apps → your app →
   Private keys → Generate a private key**. A `.pem` downloads.
2. **Replace `APP_PRIVATE_KEY` secret** with the new key contents:
   ```bash
   gh secret set APP_PRIVATE_KEY < new-app-key.pem
   ```
3. **Revoke the old key** in the same GitHub Apps UI (click "Revoke" on
   the old key row). This invalidates any tokens minted from it; in-flight
   installation tokens expire within 1 hour on their own anyway.
4. **Delete the old `.pem` file** from disk and any backups.
5. **Validate**: `gh workflow run collect.yml` — the `Mint GitHub App
   token` step should still mint successfully; first run should be green.

### What does NOT need to happen

- Re-create the App — keys are not the App identity.
- Re-install the App on the repo — installation is independent of keys.
- Update `APP_ID` — it stays the same across key rotations.

---

## 3. Refresh token (continuous, automatic)

Salesforce rotates the refresh token on every refresh (mandatory in this
org). The pipeline persists the rotated token to `SF_REFRESH_TOKEN` after
every run via `gh secret set` — see `.github/workflows/collect.yml`
`Rotate auth secret (refresh token rotation)`.

This is **not** a manual procedure; it happens automatically as long as
the GitHub App token has `permission-secrets: write` (verified in the
`Mint GitHub App token` step).

To force a fresh refresh token at any time without rotating the
External Client App: re-run `scripts/get_sf_mcp_tokens.py` with the
**existing** Consumer Key/Secret and `gh secret set SF_REFRESH_TOKEN
<<< '<new>'`.

---

## Quick reference — single command per identity

```bash
# Salesforce ECA: regenerate secret + re-bootstrap PKCE + set 3 secrets
# (must be done in browser for the Consumer Secret regeneration)
python scripts/get_sf_mcp_tokens.py "<KEY>" "<SECRET>"
gh secret set SF_CLIENT_ID     <<< '<KEY>'
gh secret set SF_CLIENT_SECRET <<< '<SECRET>'
gh secret set SF_REFRESH_TOKEN <<< '<REFRESH>'

# GitHub App: download new key + replace secret + revoke old
# (must be done in browser to download the .pem and revoke)
gh secret set APP_PRIVATE_KEY < new-app-key.pem

# Refresh token: just trigger a workflow run
gh workflow run collect.yml
```

---

## What this document does NOT cover

- **GitHub PAT fallback** — removed from the workflow on 2026-08-19
  (commit `f8117aa`). The PAT-free rotation via GitHub App is the only
  supported path; fall back to manual `gh secret set` if the App is
  uninstalled.
- **Sentry DSN rotation** — out of scope; rotate in Sentry's UI and
  `gh secret set SENTRY_DSN`.
- **SMTP/Gmail app password** — not used in this pipeline (email
  notifications were disabled in Phase 0 → re-enabled in commit
  `46032d8` but routed through a separate identity; rotate via Google
  Account security UI).
