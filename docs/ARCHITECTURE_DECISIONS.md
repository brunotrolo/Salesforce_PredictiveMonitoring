# ARCHITECTURE DECISION RECORDS (ADRs)
**Project:** Salesforce Predictive Monitoring  
**Status:** Validated (2026-08-15)

---

## ADR-001: Micro-Services Architecture

**Status:** ✅ ACCEPTED  
**Date:** 2026-08-15

### Context
The system needs to process Salesforce logs and generate risk scores. Multiple distinct operations must happen:
1. Collect logs from Salesforce
2. Analyze logs with heuristics
3. Compare against historical data (ML)
4. Generate alerts

We could monolith everything or decompose.

### Decision
Implement as **isolated micro-services** (collector, heuristic, comparison) communicating via JSON.

### Rationale
- **Isolation:** Each service can fail independently
- **Testing:** Mock each service in isolation
- **Scaling:** Different services can scale independently
- **Deployment:** Deploy services on different schedules
- **Ownership:** Different teams can own different services

### Consequences
- **Positive:**
  - Easy to test each service in isolation
  - Easy to mock Salesforce in Phase 0
  - Simple contract validation (JSON Schema)
  - Easy to parallelize development

- **Negative:**
  - Must manage inter-service contracts
  - Slightly higher latency vs monolith
  - Debugging requires tracing across services
  - More files to maintain

### Example: Phase 0 → Phase 1 Transition
```python
# No changes to heuristic or comparison services needed!
# Only collector changes:

# Phase 0:
logs = json.load("mock_logs.json")

# Phase 1:
from mcp_salesforce import SalesforceClient
logs = SalesforceClient().query_logs()

# Everything else stays the same ✅
```

### Related Decisions
- ADR-002 (JSON contracts)
- ADR-003 (Structured logging)

---

## ADR-002: JSON as Primary Data Format

**Status:** ✅ ACCEPTED  
**Date:** 2026-08-15

### Context
Services need to exchange data. Options:
1. Protocol Buffers (compact, typed)
2. XML (verbose, hierarchical)
3. JSON (human-readable, language-agnostic)
4. CSV (tabular only)
5. Binary (compact, opaque)

### Decision
Use **JSON for all inter-service communication** and storage.

### Rationale
- **Language-agnostic:** Works in Python, JavaScript, any language
- **Human-readable:** Easy debugging with `python -m json.tool`
- **Version-safe:** Optional fields are backward-compatible
- **Tooling:** Built-in support everywhere
- **Simple validation:** JSON Schema well-established

### Consequences
- **Positive:**
  - Easy to debug (print JSON and see exactly what's wrong)
  - No need for serialization libraries
  - Storage in git is human-reviewable
  - Tests can use JSON fixtures directly

- **Negative:**
  - Slightly larger file sizes than binary
  - No typing at runtime (but Pydantic compensates)
  - Performance overhead vs Protocol Buffers (negligible for monitoring)

### Example: Service Contracts
```json
{
  "collector_output": {
    "log_id": "string",
    "timestamp": "ISO8601",
    "status_code": "integer",
    "duration_ms": "integer"
  },
  
  "heuristic_output": {
    "risk_score": "float (0-1)",
    "alerts": [
      {
        "severity": "CRITICAL|WARNING|INFO",
        "message": "string",
        "timestamp": "ISO8601"
      }
    ]
  }
}
```

### Related Decisions
- ADR-001 (Micro-services)
- ADR-003 (Structured logging)

---

## ADR-003: Structured Logging with JSON Lines

**Status:** ✅ ACCEPTED  
**Date:** 2026-08-15

### Context
Services need to log operations. Options:
1. Print statements (unstructured)
2. Plain text logs (hard to parse)
3. CSV logs (tabular only)
4. JSON logs (structured, queryable)
5. Syslog (overkill for this phase)

### Decision
Use **JSON Lines format** (one JSON object per line) with `structlog`.

### Rationale
- **Queryable:** Can pipe through `grep`, `jq`, etc.
- **Searchable:** Can index and search easily
- **Traceable:** Easy to correlate requests across services
- **Metrics-ready:** Easy to parse for monitoring dashboards
- **Standard:** Industry standard in cloud platforms

### Consequences
- **Positive:**
  - Easy to track bottlenecks (filter by duration_ms)
  - Easy to find errors (filter by level=ERROR)
  - Can build dashboards on top
  - Machine-readable for alerting

- **Negative:**
  - Human-unreadable until formatted
  - Slightly more overhead than plain text
  - Requires `jq` or similar tool to read nicely

### Example: Log Output
```bash
# Raw output
cat monitoring.log | head -1
{"timestamp": "2026-08-15T10:05:00Z", "level": "info", "event": "collector_start", "service": "collector", "count": 523}

# Human-readable
cat monitoring.log | jq '.'
{
  "timestamp": "2026-08-15T10:05:00Z",
  "level": "info",
  "event": "collector_start",
  "service": "collector",
  "count": 523
}
```

### Related Decisions
- ADR-002 (JSON data format)
- ADR-004 (Logging in CI/CD)

---

## ADR-004: Mock-First Strategy for Phase 0

**Status:** ✅ ACCEPTED  
**Date:** 2026-08-15

### Context
Building monitoring system that depends on Salesforce API. The API:
- Requires authentication credentials
- Has rate limits
- Cannot be tested repeatedly without cost
- Adds risk if not working

Options:
1. Integrate with real Salesforce from day 1 (high risk)
2. Use mocks for Phase 0, switch in Phase 1 (low risk)
3. Use mocks forever (high risk of Phase 1 surprise failures)

### Decision
**Mock-first strategy:** Phase 0 uses only mock data. Phase 1 switches to real Salesforce.

### Rationale
- **Validation:** Proves architecture works without external dependencies
- **Testing:** Can run full pipeline locally without auth
- **Parallel work:** Frontend and backend can work independently
- **Risk reduction:** Catch architectural issues before Salesforce integration
- **Speed:** Faster iteration in Phase 0

### Consequences
- **Positive:**
  - Phase 0 can complete in 3-4 days
  - Full test coverage before touching Salesforce
  - Easy to validate pipeline end-to-end
  - Team ramp-up faster (no Salesforce setup)

- **Negative:**
  - Must handle Phase 0 → Phase 1 transition carefully
  - Mocks must be realistic (representative)
  - Real Salesforce might have surprises in Phase 1

### Phase 0 → Phase 1 Transition Plan
```python
# Phase 0 (collector.py)
def get_logs():
    with open("mock_logs.json") as f:
        return json.load(f)

# Phase 1 (1-2 line change!)
def get_logs():
    from mcp_salesforce import SalesforceClient
    return SalesforceClient().query_logs()

# Heuristic, comparison, dashboard: ZERO CHANGES
```

### Related Decisions
- ADR-001 (Micro-services)
- ADR-005 (Testing strategy)

---

## ADR-005: Test Pyramid with Mocks

**Status:** ✅ ACCEPTED  
**Date:** 2026-08-15

### Context
Need to ensure quality without hitting external APIs. Options:
1. No tests (risky)
2. Only end-to-end tests (slow, flaky)
3. Mix of unit, integration, end-to-end (recommended)

### Decision
Implement **test pyramid**: Many unit tests (mocked), fewer integration tests, one full pipeline test.

```
        ▲
       /|\    E2E (1 test)
      / | \   Pipeline validates complete flow
     /  |  \
    /─────────\  Integration (5-10 tests)
   /   |   |   \ Service contracts validated
  /─────────────\ Unit (50+ tests, mocked)
 /____|____|____\ Individual functions
```

### Rationale
- **Speed:** Unit tests run in <100ms
- **Debugging:** Failures are localized
- **Coverage:** High coverage with low flakiness
- **Mocking:** Easy to test Salesforce interactions
- **Scalability:** Works as codebase grows

### Target Coverage
- **Backend:** ≥80% code coverage
- **Frontend:** ≥70% code coverage
- **Critical paths:** 100% coverage

### Consequences
- **Positive:**
  - Tests are fast (CI completes in <5 minutes)
  - Debugging is easy (knows exactly which unit failed)
  - High confidence in code quality
  - Easy to measure progress

- **Negative:**
  - Must maintain mocks
  - Mocks can drift from reality
  - Still need some real integration tests

### Example: Test Levels

**Unit Test** (Fast, Mocked)
```python
def test_heuristic_calculates_risk_score():
    heuristic = Heuristic()
    logs = [{"status_code": 500}, {"status_code": 200}]
    result = heuristic.analyze(logs)
    assert result.risk_score == 0.25  # 1 error / 2 logs
```

**Integration Test** (Medium, Real Mocks)
```python
def test_collector_to_heuristic_pipeline():
    collector = Collector(data_source=mock_salesforce_logs)
    heuristic = Heuristic()
    logs = collector.get_logs()
    result = heuristic.analyze(logs)
    assert result.risk_score >= 0
    assert len(result.alerts) >= 0
```

**E2E Test** (Slow, Full Pipeline)
```python
def test_full_monitoring_pipeline():
    # Collector → Heuristic → JSON → Dashboard
    orchestrate()
    result = read_json_output()
    assert result["health_check"]["status"] in ["HEALTHY", "WARNING"]
```

### Related Decisions
- ADR-004 (Mock-first)
- ADR-002 (JSON contracts)

---

## ADR-006: GitHub Actions + GitHub Pages Deployment

**Status:** ✅ ACCEPTED  
**Date:** 2026-08-15

### Context
Need to run collection schedule (15-minute interval) and deploy dashboard. Options:
1. Self-hosted server (cost, maintenance)
2. Cloud function (AWS Lambda, Google Cloud, Azure) (cost, complexity)
3. GitHub Actions (free, included)
4. Cron job on laptop (unreliable)

### Decision
Use **GitHub Actions for orchestration** and **GitHub Pages for deployment**.

### Rationale
- **Cost:** $0/month (included with GitHub)
- **No ops:** No servers to manage
- **Reliability:** GitHub's infrastructure
- **Simple:** YAML configuration
- **Built-in:** No third-party dependencies
- **Storage:** Use git branches as data store

### Consequences
- **Positive:**
  - No infrastructure cost
  - No authentication complexity (GitHub Action token)
  - Easy to schedule (cron expressions)
  - Logs visible in GitHub UI
  - History preserved in git

- **Negative:**
  - GitHub Actions has rate limits (but generous)
  - Cannot run in parallel easily
  - No database (but JSON + git works)
  - Vendor lock-in to GitHub

### Architecture
```
GitHub Actions (Scheduler)
  ├─ Every 15 minutes → Run collector
  ├─ Every 4 hours → Run ML comparison
  └─ Every commit → Run tests + deploy
        ↓
    JSON output (risk_scores.json, alerts.json)
        ↓
    Persist to data/ branch (git)
        ↓
    GitHub Pages (serves static HTML)
        ↓
    Frontend fetches from data/ via fetch()
```

### Related Decisions
- ADR-001 (Micro-services)
- ADR-003 (Structured logging)

---

## ADR-007: MCP Salesforce Over Direct OAuth

**Status:** ✅ ACCEPTED  
**Date:** 2026-08-15

### Context
Need to connect to Salesforce API. Options:
1. Direct OAuth flow (complex, error-prone)
2. MCP Salesforce (abstracted, managed)
3. Salesforce CLI (local-only)
4. Direct SOAP/REST (low-level)

### Decision
Use **Model Context Protocol (MCP) Salesforce** for API abstraction.

### Rationale
- **Simplification:** 90% less OAuth boilerplate
- **Managed:** Token refresh, retry logic built-in
- **Safety:** No need to store credentials in code
- **Rate limiting:** Automatic backoff handling
- **Testing:** Easy to mock without real credentials

### Consequences
- **Positive:**
  - Phase 0 → Phase 1 transition is 1-2 lines
  - No credential management headaches
  - Automatic error handling
  - Built-in rate limiting

- **Negative:**
  - Dependency on MCP (but it's maintained)
  - One more abstraction layer
  - Need to test MCP in GitHub Actions (Phase 1)

### Example: Integration
```python
# Phase 1 only
from mcp_salesforce import SalesforceClient

client = SalesforceClient()
logs = client.soql_query("SELECT * FROM Log__c WHERE CreatedDate > :yesterday")
```

### Related Decisions
- ADR-004 (Mock-first)
- ADR-001 (Micro-services)

---

## ADR-008: No Database (Git as Datastore)

**Status:** ✅ ACCEPTED  
**Date:** 2026-08-15

### Context
Need to persist historical data (risk_scores over time). Options:
1. Relational database (PostgreSQL, MySQL) (cost, ops)
2. NoSQL (DynamoDB, MongoDB) (cost, learning curve)
3. Time-series DB (InfluxDB, Prometheus) (cost)
4. Git repository (free, versioned)
5. CSV files (simple, limited)

### Decision
Use **Git as the datastore**: Persist JSON to `data/` branch, one directory per day.

### Rationale
- **Cost:** $0 (GitHub storage is free)
- **Versioning:** Full history in git
- **Simplicity:** No database to maintain
- **Queryable:** Can use git to find changes
- **Portable:** Just clone the repo
- **Collaborative:** Easy for team to review data

### Consequences
- **Positive:**
  - No database administration
  - History is immutable (git log)
  - Easy backup (clone repo)
  - Easy to share (push to GitHub)

- **Negative:**
  - Not optimal for real-time queries
  - Git repo gets large over time (mitigated by squash)
  - Cannot do complex joins (mitigated by Phase 3 ML)
  - Scaling limits (millions of rows would be slow)

### Storage Structure
```
data/              (separate branch)
├── 2026-08-15/
│   ├── risk_scores.json    (array of daily scores)
│   ├── alerts.json         (array of alerts)
│   └── metadata.json       (run timestamp, status)
├── 2026-08-16/
│   └── ...
└── 2026-08-17/
    └── ...
```

### Related Decisions
- ADR-006 (GitHub Actions)
- ADR-002 (JSON format)

---

## ADR-009: Pydantic for Data Validation

**Status:** ✅ ACCEPTED  
**Date:** 2026-08-15

### Context
Services exchange JSON. Need validation. Options:
1. Manual if/else checks (error-prone)
2. JSON Schema validators (external tool)
3. Pydantic models (Python library, type hints)
4. No validation (risky)

### Decision
Use **Pydantic models** for runtime validation with automatic serialization.

### Rationale
- **Type-safe:** Leverage Python type hints
- **Fast validation:** Runs on every input
- **Automatic:** Serializes/deserializes JSON automatically
- **IDE-friendly:** Type hints help autocomplete
- **Error messages:** Clear validation errors

### Example
```python
from pydantic import BaseModel, field_validator

class Log(BaseModel):
    log_id: str
    status_code: int
    duration_ms: int
    timestamp: str
    
    @field_validator("status_code")
    def status_must_be_valid(cls, v):
        if v < 0 or v > 599:
            raise ValueError("HTTP status must be 0-599")
        return v

# Usage
logs_json = [{"log_id": "L1", "status_code": 200, ...}]
logs = [Log(**log) for log in logs_json]  # Validates automatically
```

### Consequences
- **Positive:**
  - Type safety catches bugs early
  - Clear error messages when data is invalid
  - Easy to generate API docs
  - Works with IDE autocomplete

- **Negative:**
  - One more dependency
  - Slight runtime overhead (negligible)
  - Learning curve for team

### Related Decisions
- ADR-002 (JSON format)
- ADR-005 (Testing)

---

## ADR-010: Tailwind CSS for Frontend Styling

**Status:** ✅ ACCEPTED  
**Date:** 2026-08-15

### Context
Need to style monitoring dashboard. Options:
1. Vanilla CSS (flexible, no build)
2. Bootstrap (heavy, opinionated)
3. Tailwind CSS (utility-first, lightweight)
4. Material Design (heavy, complex)
5. Styled components (requires build)

### Decision
Use **Tailwind CSS** for utility-first styling.

### Rationale
- **No build required:** CDN link in HTML
- **Lightweight:** Only includes used classes
- **Responsive:** Mobile-first, responsive utilities
- **Dark mode:** Built-in dark mode support
- **Accessibility:** Includes WCAG utilities

### Example
```html
<!-- Dark mode + responsive + accessible -->
<div class="dark:bg-gray-900 bg-white p-4 sm:p-8 md:p-12">
  <h1 class="text-2xl sm:text-3xl dark:text-white font-bold">
    Monitoring Dashboard
  </h1>
</div>
```

### Consequences
- **Positive:**
  - No CSS build step
  - Easy to iterate (change HTML, refresh)
  - Consistent spacing (design system)
  - Mobile-friendly out of box

- **Negative:**
  - Learning curve (utility-first paradigm)
  - HTML can get verbose
  - Requires CDN for full-featured experience

### Related Decisions
- None specific (frontend decision)

---

## ADR-011: Agent Skills Pack Vendored at Repo Root

**Status:** ✅ ACCEPTED  
**Date:** 2026-08-16

### Context
The project uses agent skills (Claude Code, OpenCode, Codex, Gemini, Copilot) with per-tool install locations (`.claude/skills`, `.agents/skills`, `.codex/`, `.github/skills`). These are machine-local installs and should not be versioned. We need a single canonical, versioned copy of the skills pack.

Options:
1. Git submodule (external repo)
2. Vendor full pack at repo root (`agent-skills/`)
3. Symlinks from per-tool locations into a shared folder

### Decision
Vendor the complete agent-skills pack in **`agent-skills/` at the repo root**. Per-tool install locations (`.claude/`, `.agents/`, `.codex/`, `.github/{agents,hooks,skills}`) remain machine-local, are **git-ignored**, and reference the canonical pack.

### Rationale
- **Single source of truth**: the pack is versioned with the code it supports
- **No external dependency**: works offline, no submodule sync issues
- **Auditability**: skill changes appear in git history alongside code changes
- **Portability**: a fresh clone gets both code and skills
- Avoids submodule complexity (per user decision)

### Consequences
- **Positive:**
  - Skills evolve in lockstep with the repo
  - No submodule maintenance
  - Any agent tool can point to the same pack

- **Negative:**
  - Repo contains agent-tooling content (noise for non-agent users)
  - Local installs can drift from the canonical pack (mitigated by git-ignoring them)

### Related Decisions
- ADR-006 (GitHub Actions)
- SECURITY_AUDIT (tooling dirs git-ignored)

---

## ADR-012: Per-Service pytest Configuration

**Status:** ✅ ACCEPTED  
**Date:** 2026-08-16

### Context
Backend is split into micro-services (ADR-001) each with its own `src/` package. Tests need to import from `src/` and measure coverage per service.

Options:
1. Single root pytest config + `conftest.py` injecting `sys.path`
2. Per-service `pytest.ini` with `pythonpath = src`
3. Editable installs (`pip install -e`) per service

### Decision
Each service owns a **`pytest.ini`** with `testpaths = tests`, `pythonpath = src`, and `addopts = --cov=src --cov-report=term-missing`. Tests run from the service directory.

### Rationale
- **Zero install step**: no packaging needed in Phase 0
- **Isolated coverage**: `--cov=src` measures exactly the service under test
- **Matches micro-service isolation**: each service's test loop is self-contained (ADR-001, ADR-005)
- No shared `conftest.py` cross-contamination

### Consequences
- **Positive:**
  - Fast, isolated test loops (`cd services/collector && pytest`)
  - Coverage numbers are meaningful per service
  - Works without any build/packaging tooling

- **Negative:**
  - No single root `pytest` command (CI must loop over services)
  - `pythonpath` is pytest-only; other tools don't see `src/` (orchestrator handles this via ADR-014)

### Related Decisions
- ADR-001 (Micro-services)
- ADR-005 (Test pyramid)
- ADR-014 (Orchestrator imports)

---

## ADR-013: Jest ESM via npx --node-options (Windows Workaround)

**Status:** ✅ ACCEPTED  
**Date:** 2026-08-16

### Context
Frontend tests run with Jest on ESM (`"type": "module"` in package.json). Jest 29 requires `--experimental-vm-modules` for ESM. On Windows, setting `NODE_OPTIONS` as an env var in npm scripts is unreliable (cross-env needed).

Options:
1. `NODE_OPTIONS=--experimental-vm-modules jest` (POSIX only)
2. `cross-env NODE_OPTIONS=... jest` (extra dependency)
3. `npx --node-options=--experimental-vm-modules jest` (cross-platform, no dependency)

### Decision
Use **`npx --node-options=--experimental-vm-modules jest --coverage`** in npm scripts.

### Rationale
- **Cross-platform**: works on Windows and POSIX without `cross-env`
- **No extra dependency**: npx is bundled with npm
- `--node-options` passes V8 flags to the Node process spawned by npx — exactly what Jest ESM needs

### Consequences
- **Positive:**
  - One command works for all devs (Windows + macOS/Linux)
  - No `cross-env` in devDependencies

- **Negative:**
  - Slightly opaque (why `npx`? — documented in package.json scripts)
  - If Jest upgrades to native ESM support, this workaround becomes removable

### Related Decisions
- ADR-005 (Test pyramid)
- ADR-010 (Frontend stack)

---

## ADR-014: Orchestrator Imports Services via sys.path

**Status:** ✅ ACCEPTED  
**Date:** 2026-08-16

### Context
`monitoring/orchestrate.py` must import the three services (`collector`, `heuristic`, `comparison`) plus `shared`. Services live under `services/<name>/src/` without packaging (ADR-012).

Options:
1. `sys.path.insert` of each `src/` dir
2. Editable installs (`pip install -e services/*`)
3. Move orchestrator inside a service package
4. pyproject/workspace packaging (uv, hatch)

### Decision
In Phase 0, the orchestrator uses **`sys.path.insert`** for the four service `src/` directories at import time (orchestrate.py:12-15). Revisit in Phase 1 (see consequences).

### Rationale
- **Zero install**: the pipeline runs with stock Python + requirements
- **Phase 0 is mock-only**: no deployment surface, no environment guarantees needed yet
- Consistent with ADR-012's "no packaging" choice

### Consequences
- **Positive:**
  - `python monitoring/orchestrate.py --mode mock` works immediately after pip install -r requirements
  - No editable-install side effects

- **Negative:**
  - Fragile: path order matters, `sys.path` pollution, breaks if layout changes
  - **Phase 1 action**: replace with editable installs or packaging (pyproject) before real deployment
  - The hack is the reason orchestrate.py needs its own test (see REVIEW_FINDINGS)

### Related Decisions
- ADR-001 (Micro-services)
- ADR-012 (Per-service pytest)
- REVIEW_FINDINGS (orchestrate.py test gap)

---

## DECISION MATRIX

| Decision | Phase | Status | Risk | Reversible? |
|----------|-------|--------|------|------------|
| Micro-services (ADR-001) | 0+ | Accepted | Low | Yes (with effort) |
| JSON format (ADR-002) | 0+ | Accepted | Low | Yes (change services) |
| Structured logging (ADR-003) | 0+ | Accepted | Low | Yes (rework logging) |
| Mock-first (ADR-004) | 0→1 | Accepted | Medium | Yes (Phase 1 transition) |
| Test pyramid (ADR-005) | 0+ | Accepted | Low | Yes (add/remove tests) |
| GitHub Actions (ADR-006) | 1+ | Accepted | Low | Yes (switch to CI/CD) |
| MCP Salesforce (ADR-007) | 1+ | Accepted | Medium | Yes (switch to OAuth) |
| Git datastore (ADR-008) | 1+ | Accepted | Medium | Yes (add database) |
| Pydantic (ADR-009) | 0+ | Accepted | Low | Yes (manual validation) |
| Tailwind CSS (ADR-010) | 0+ | Accepted | Low | Yes (new CSS framework) |
| Agent skills vendored (ADR-011) | 0+ | Accepted | Low | Yes (switch to submodule) |
| Per-service pytest (ADR-012) | 0+ | Accepted | Low | Yes (root config) |
| Jest ESM via npx (ADR-013) | 0+ | Accepted | Low | Yes (cross-env or native ESM) |
| sys.path orchestrator (ADR-014) | 0→1 | Accepted | Medium | Yes (Phase 1: editable installs) |

---

## WHEN TO REVISIT THESE DECISIONS

| Trigger | Decision to Review |
|---------|-------------------|
| Repo size > 500MB | ADR-008 (Git datastore) |
| Coverage drops below 70% | ADR-005 (Test strategy) |
| Phase 1 MCP fails | ADR-007 (Switch to OAuth) |
| Single service bottleneck | ADR-001 (Monolith?) |
| Deployment issues | ADR-006 (Consider K8s?) |
| Data query needs complex joins | ADR-008 (Add database?) |

---

**Last Updated:** 2026-08-16  
**Next Review:** Start of Phase 1 (2026-08-22)

All decisions are **ACCEPTED** and ready for implementation.

Questions? Create Issue or discuss in team standup.
