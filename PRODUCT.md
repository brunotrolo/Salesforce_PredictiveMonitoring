# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Single operator: the store owner (Bruno) running an eCommerce app whose integrations with Salesforce are the load-bearing path. He checks the dashboard in short, periodic sessions — a glance to confirm "everything is fine", a deeper look when an alert or a slow day demands it. The dashboard is a tool, not a destination; it must answer in seconds and never obscure the state with decoration.

## Product Purpose

24/7 predictive monitoring of the Salesforce integration health of an eCommerce store: a cron collects real Salesforce logs every 15 minutes, a heuristic scores integration risk, a comparison layer tracks change vs baseline, and everything is persisted as JSON on a git branch (ADR-008: Git as datastore). The dashboard is the human window into that pipeline: current risk, alerts, trend, and pipeline health — at zero cost, with no backend of its own.

## Positioning

Prediction over logs: the pipeline produces a risk score, a change prediction (STABLE vs drift) and a confidence — a judgment, not a log dump. The mechanism is a 15-minute collection loop backed by a real Salesforce query, with the entire datastore being a git branch anyone can read.

## Operating Context

- Collection: `.github/workflows/collect.yml` (15-min cron) → MCP Salesforce query → heuristic + comparison → snapshot JSON committed to the `data/` branch (`data/<day>/<timestamp>.json`).
- Hosting: GitHub Pages, classic build serving `main/docs` via Jekyll 3.10. Static ES modules, no framework, no build step, no dependencies.
- Data access: the dashboard fetches from `raw.githubusercontent.com` and the GitHub Contents API (unauthenticated public repo; rate limits are a real constraint on very frequent refreshes).
- Language: interface in Brazilian Portuguese; product name in English.
- Offline behavior: when the data branch is unreachable, the fetcher falls back to mock data — the dashboard must always render and clearly label mock vs real.

## Capabilities and Constraints

- Snapshot shape (real): `risk_score` (0–1), `errors_count`, `slow_requests_count`, `alerts[]` (severity, message, log_id), `comparison` (prediction, confidence, risk_delta, summary), `health_check` (status, last_updated), `validation` (valid, errors), `logs_processed`, `mode` (`real`|`mock`), `timestamp`.
- Risk levels: >= 0.7 CRITICAL, >= 0.4 WARNING, below HEALTHY (thresholds live in `site/monitoring/dashboard.js`).
- Real alerts carry `log_id` and NO `timestamp`/`id` (mock data has `id`/`timestamp`) — the UI must not depend on per-alert timestamps.
- `Log__c` has no duration field (only `Status__c`, `Endpoint__c`, `Method__c`), so "slow requests" come from whatever the collector derives; count may be 0.
- Canonical fetcher is `site/api/client.js` (tested, 12 tests) — the published page consumes a synced mirror under `docs/dashboard/assets/` produced by `site/scripts/sync-dashboard.mjs`; never hand-edit the mirror.
- GitHub Pages serves ONLY `docs/`; the dashboard therefore lives at `docs/dashboard/`.
- Jekyll processes `index.html` with Liquid: no `{{` / `{%` sequences in HTML files.

## Brand Commitments

Product name: "Salesforce Predictive Monitoring". No other binding visual identity exists; the owner confirmed a dark, technical, precise register (observability style) and pt-BR interface.

## Evidence on Hand

- Real snapshots: branch `data/`, e.g. `data/2026-08-16/2026-08-16T17-15-18Z.json` (mode real, risk 0.03, 10 CRITICAL alerts, comparison STABLE, validation valid, 100 logs processed).
- Mock fixtures: `site/monitoring/mock-data.js` (mockMonitoringData, mockEmptyData, mockCriticalData).
- Tests: `site/api/tests/test-client.js` (fetcher contract), `site/monitoring/tests/test-dashboard.js` (risk levels, formatting).
- `SPECIFICATION.md` §3.2 defines the dashboard as the Phase 1 deliverable (currently marked "página HTML não publicada").

## Product Principles

1. Truth over decoration: real data and mock data are visibly distinct; nothing is invented when the pipeline is silent.
2. Answer in seconds: the first viewport settles "is the store's integration healthy?" — risk, alerts, and trend without hunting.
3. Zero-cost robustness: static files, no dependencies, offline fallback; the page must never hang waiting on GitHub.
4. Single source of truth: canonical modules live in `site/` with tests; published copies are generated mirrors, never hand-edited.
5. The operator owns the state: refresh is explicit, states (loading/empty/mock/error) are named and recoverable.