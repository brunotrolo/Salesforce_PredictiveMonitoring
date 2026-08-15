# CLAUDE CODE SKILLS - 6-PHASE AGENT FRAMEWORK
**Projeto:** Salesforce Predictive Monitoring  
**Data:** 2026-08-15  
**Framework:** Agent-Skills (Spec → Plan → Build → Test → Review → Ship)

---

## 📌 OVERVIEW

Claude Code Skills are native platform resources accessed via slash commands (`/comando`). This document maps each skill to the 6-phase agent-skills framework, showing when and how to use each skill throughout the project lifecycle.

**Framework Structure:**
```
Phase 1: SPEC       /spec       → Specification
Phase 2: PLAN       /plan       → Planning & Architecture
Phase 3: BUILD      /build      → Execution & Implementation
Phase 4: TEST       /test       → Test-Driven Development
Phase 5: REVIEW     /code-review → Code Audit (3 subagents)
Phase 6: SHIP       /ship       → Pre-Launch Validation
```

---

## 🎯 PHASE 1: SPECIFICATION (`/spec`)

### Objective
Define project requirements, scope, acceptance criteria, and validation strategy before any planning or coding.

### What it does
Analyzes requirements, generates structured specifications, validates completeness, creates traceability matrix.

### How to use
```bash
/spec
(Describe project goals, constraints, and success metrics)
```

### Salesforce PM Project Usage
```
Input:
  "Criar sistema de monitoramento preditivo para Salesforce logs.
   - Entrada: Logs via MCP Salesforce
   - Processamento: Heurística (Phase 0) + ML (Phase 3)
   - Saída: Risk scores + Alerts + Dashboard
   - Timeline: 4-5 semanas
   - Equipe: 3 pessoas
   - Custo: $0/mês"

Output (/spec generates):
  ✓ Requirement categories (functional, non-functional, security, performance)
  ✓ Acceptance criteria for each phase
  ✓ Success metrics (test coverage, latency, uptime)
  ✓ Risk identification
  ✓ Traceability matrix (requirements → tests → code)
  ✓ Definition of Done for each phase
```

### When to use
- ✅ **Phase 1 START:** Once per project (before all other phases)
- ✅ **Phase boundaries:** When scope changes

### Outputs
- **SPECIFICATION.md:** Consolidated requirements
- **Acceptance criteria:** Testable, measurable requirements
- **Traceability matrix:** Requirements ↔ Tests ↔ Code

### Benefits
- Clear, unambiguous requirements
- All team members aligned
- Foundation for all subsequent phases
- Reduced rework

### Checklist
- [ ] All requirements documented
- [ ] Acceptance criteria defined (SMART)
- [ ] Success metrics identified
- [ ] Risks acknowledged
- [ ] Traceability matrix complete
- [ ] Team alignment confirmed

---

## 🎯 PHASE 2: PLANNING (`/plan`)

### Objective
Convert specifications into actionable plans with architecture, resource allocation, timeline, and risk mitigation.

### What it does
Creates implementation roadmap, identifies dependencies, allocates resources, generates architecture diagrams, defines milestones.

### How to use
```bash
/plan
(Provide specification and project constraints)
```

### Salesforce PM Project Usage
```
Input (from /spec):
  SPECIFICATION.md + Project constraints

Output (/plan generates):
  ✓ 6-phase roadmap (Phase 0-5, 4-5 weeks)
  ✓ Phase breakdown:
    - Phase 0 (3-4 days): Mock architecture + tests
    - Phase 1 (5-7 days): Real Salesforce integration
    - Phase 2-5 (4 weeks): Features (alerts, ML, feedback, hardening)
  ✓ Resource allocation: Backend (3w), Frontend (2w), DevOps (1w)
  ✓ Architecture: Micro-services (collector, heuristic, comparison, shared)
  ✓ Tech stack: Python 3.10+, Node 18+, GitHub Actions
  ✓ Risk mitigation: MCP failure handling, data growth, model accuracy
  ✓ Cost analysis: $0/month (GitHub Actions, Pages, existing Salesforce)
  ✓ Critical dependencies:
    - Phase 0: pytest, Jest, Tailwind CSS, structlog
    - Phase 1: MCP Salesforce, pandas
    - Phase 3: Prophet, scikit-learn
```

### When to use
- ✅ **Phase 2 START:** Once per phase (or scope change)
- ✅ **After /spec:** Immediately after specification complete
- ✅ **Re-plan:** If major blockers identified

### Outputs
- **PROJECT_ROADMAP_MASTER.md:** Timeline + milestones
- **Architecture diagram:** Service boundaries
- **Resource allocation:** Team capacity per phase
- **Risk register:** Mitigation strategies

### Benefits
- Predictable timeline
- Clear dependencies and critical path
- Resource efficiency
- Risk visibility
- Stakeholder confidence

### Checklist
- [ ] All phases have milestones
- [ ] Resource allocation realistic
- [ ] Dependencies identified
- [ ] Critical path visible
- [ ] Risk mitigation strategies defined
- [ ] Team capacity validated

---

## 🎯 PHASE 3: BUILD (`/build`)

### Objective
Execute implementation based on plan. Generate scaffold, write production code, create test stubs, establish CI/CD.

### What it does
Generates project scaffold, creates directory structure, writes implementation code, establishes build pipeline, generates initial tests.

### How to use
```bash
/build
(Describe what needs to be built, from specification and plan)
```

### Salesforce PM Project Usage
```
Input (from /spec + /plan):
  "Build Phase 0 scaffold:
   - services/collector/ (mock log generator)
   - services/heuristic/ (risk score calculation)
   - services/shared/ (common utilities)
   - site/monitoring/ (mock dashboard)
   - .github/workflows/ (test.yml + deploy.yml)
   - tests/ (initial pytest + Jest structure)"

Output (/build generates):
  ✓ Project scaffold (directory structure)
  ✓ services/collector/src/collector.py (mock data generation)
  ✓ services/heuristic/src/heuristic.py (risk score logic)
  ✓ services/shared/src/logger.py (JSON logging)
  ✓ site/monitoring/index.html + dashboard.js (mock UI)
  ✓ .github/workflows/test.yml (pytest + Jest CI)
  ✓ services/*/tests/test_*.py (test stubs)
  ✓ site/monitoring/tests/test-*.js (frontend test stubs)
  ✓ pyproject.toml + requirements.txt (Phase 0 dependencies)
  ✓ package.json + npm scripts (frontend setup)
  ✓ Initial pre-commit hooks (.pre-commit-config.yaml)
```

### When to use
- ✅ **Phase 3 START:** Once per phase
- ✅ **After /plan:** Immediately after planning complete
- ✅ **Feature branches:** When building new services

### Outputs
- **Project scaffold:** directories, files, git setup
- **Source code:** implementation of core services
- **Test structure:** test files, fixtures, conftest.py
- **CI/CD pipeline:** GitHub Actions workflows
- **Dependencies:** pyproject.toml, package.json

### Benefits
- Consistent project structure
- All files created at once
- Foundation for team work
- CI/CD ready immediately
- Reduced setup time

### Checklist
- [ ] All directories created
- [ ] Source files generated
- [ ] Test stubs present
- [ ] CI/CD pipeline active
- [ ] Dependencies installed
- [ ] Team can build locally
- [ ] No compilation errors

---

## 🎯 PHASE 4: TEST (`/test`)

### Objective
Ensure code meets specification through comprehensive testing (unit, integration, E2E). Close gaps between implementation and requirements.

### What it does
Generates test cases based on acceptance criteria, implements TDD cycle, validates coverage targets, identifies gaps, generates test reports.

### How to use
```bash
/test
(Describe what needs testing, from specification)
```

### Salesforce PM Project Usage
```
Input (from /spec + code):
  "Test Phase 0 implementation:
   - Requirement: All services output valid JSON
   - Requirement: Risk score in range [0, 1]
   - Requirement: Tests ≥80% backend, ≥70% frontend
   - Requirement: Heuristic identifies 5 alert types
   - Requirement: Dashboard loads in <2s"

Output (/test generates):
  ✓ Test cases (pytest + Jest):
    - services/collector/tests/: Data generation tests
    - services/heuristic/tests/: Risk score calculation tests
    - services/shared/tests/: Logger + utilities tests
    - site/monitoring/tests/: Dashboard component tests
  ✓ Test fixtures (mock data):
    - services/*/tests/fixtures/mock_logs.yaml
    - services/*/tests/fixtures/mock_risks.yaml
  ✓ Coverage report:
    - Backend: 82% (exceeds 80% target)
    - Frontend: 75% (exceeds 70% target)
  ✓ Gap analysis:
    - Missing: E2E test for collector → heuristic → dashboard
    - Missing: Performance test for <2s dashboard load
  ✓ Test report (pytest/Jest HTML report)
  ✓ Pre-commit hooks (auto-run tests on commit)
```

### When to use
- ✅ **Phase 4 START:** Once per phase
- ✅ **After /build:** Immediately after implementation complete
- ✅ **TDD cycle:** Generate tests, implement code, iterate

### Outputs
- **Test suite:** pytest + Jest test files
- **Fixtures:** Mock data for testing
- **Coverage report:** Line coverage by module
- **Gap analysis:** Missing tests identified
- **Test report:** Pass/fail results

### Benefits
- Confidence in implementation
- Fast feedback loop (pre-commit validation)
- Coverage targets met
- Requirements verified
- Regression prevention

### Checklist
- [ ] All acceptance criteria have tests
- [ ] Coverage targets met (80/70)
- [ ] All tests passing
- [ ] Fixtures complete
- [ ] Gap analysis addressed
- [ ] Pre-commit hooks working
- [ ] CI/CD test pipeline green

---

## 🎯 PHASE 5: REVIEW (`/code-review`)

### Objective
Audit code for bugs, security, performance, maintainability before shipping. Ensure production-readiness.

### What it does
Deep code analysis with 3 subagents (code reviewer, security auditor, test engineer). Identifies issues, suggests improvements, validates best practices.

### How to use
```bash
/code-review              # Low effort (quick scan)
/code-review medium       # Medium effort (balanced)
/code-review high         # High effort (comprehensive)
```

### Salesforce PM Project Structure (3 Subagents)

#### Subagent 1: Code Reviewer
**Focus:** Bugs, performance, maintainability, style

```
/code-review high
(Reviews services/heuristic/src/heuristic.py for risk score calculation)

Validates:
  ✓ No off-by-one errors in risk thresholds
  ✓ Algorithm correctness (weights sum to 1.0)
  ✓ Variable naming clarity
  ✓ Function complexity (cyclomatic complexity < 10)
  ✓ Docstring presence
  ✓ Performance: O(n) vs O(n²) for large log sets
  ✓ Error handling for edge cases
```

#### Subagent 2: Security Auditor
**Focus:** Auth, injection, data exposure, compliance

```
/code-review high --security
(Reviews MCP Salesforce integration for Phase 1)

Validates:
  ✓ No credentials hardcoded
  ✓ Input sanitization (logs from Salesforce)
  ✓ Rate limiting compliance (MCP built-in)
  ✓ TLS/HTTPS for all external calls
  ✓ No PII exposure in logs
  ✓ Session management (if applicable)
  ✓ Access control validation
```

#### Subagent 3: Test Engineer
**Focus:** Test quality, coverage, edge cases

```
/code-review high --test
(Reviews test suite for collector service)

Validates:
  ✓ Coverage: All code paths tested
  ✓ Edge cases: Empty logs, malformed JSON
  ✓ Fixtures: Representative test data
  ✓ Mocking: External dependencies isolated
  ✓ Assertions: Each test has clear assertion
  ✓ Performance: Tests complete in <5s
  ✓ Flakiness: No timing-dependent failures
```

### Salesforce PM Project Usage - Phase 0 Example

```
Phase 0: Review all pull requests with /code-review medium

PR: feat/heuristic-v1
  /code-review medium --comment
  
  Findings:
    ✗ BUG: Risk score calculation uses weights [0.4, 0.3, 0.2, 0.1] = 1.0 ✓
    ✗ PERF: O(n²) nested loop in alert detection → suggest vectorization
    ✗ TEST: Missing edge case (empty logs list)
    ✓ STYLE: Docstrings clear, names descriptive
    ✓ SECURITY: No credentials exposed
    
  Action: Fix perf issue, add edge case test, re-review
```

### When to use
- ✅ **Phase 5 START:** Once per PR (before merge)
- ✅ **Phase 0:** Every Python PR (services/)
- ✅ **Phase 1:** MCP integration PRs
- ✅ **Phase 3:** ML logic (Prophet, Isolation Forest)
- ✅ **All phases:** All backend code

### Outputs
- **Findings:** Categorized by severity (bug, perf, style, security)
- **Suggestions:** Specific code improvements
- **Inline comments:** Line-by-line on GitHub
- **Report:** Summary of issues and fixes applied

### Benefits
- Catch bugs before production
- Knowledge transfer (code review as documentation)
- Security vulnerabilities identified early
- Performance regressions prevented
- Test quality assured

### Checklist
- [ ] Code reviewer sign-off
- [ ] Security auditor sign-off
- [ ] Test engineer sign-off
- [ ] All severity-critical issues fixed
- [ ] Inline comments addressed
- [ ] PR comments replied
- [ ] Ready to merge

---

## 🎯 PHASE 6: SHIP (`/ship`)

### Objective
Final validation before deploying to production. Ensure system is ready, deployment pipeline works, rollback strategy exists.

### What it does
Final pre-launch checks, validates deployment pipeline, ensures monitoring/alerts active, confirms rollback procedure, generates deployment checklist.

### How to use
```bash
/ship
(Describe what's being deployed and environment)
```

### Salesforce PM Project Usage - Phase 0 Complete Example

```
Input:
  "Deploy Phase 0 to GitHub Pages:
   - Artifact: site/monitoring/ (static HTML/JS)
   - Pipeline: .github/workflows/deploy.yml
   - Environment: GitHub Pages (public)
   - Success metric: Dashboard accessible at github.io
   - Rollback: Revert commit, re-run workflow"

Output (/ship generates):
  ✓ Pre-deployment checklist:
    - All tests passing? ✓
    - Coverage targets met? ✓
    - Code review approved? ✓
    - Security scan clean? ✓
    - Documentation updated? ✓
    
  ✓ Deployment validation:
    - GitHub Pages deployed? ✓
    - Dashboard loads? ✓
    - No 404 errors? ✓
    - Dark mode works? ✓
    - Responsive on mobile? ✓
    
  ✓ Monitoring setup:
    - GitHub Actions logs viewable? ✓
    - Workflow failure alerts configured? ✓
    - Error tracking enabled? (Phase 5+)
    
  ✓ Rollback procedure:
    - Previous deployment accessible? ✓
    - Git history maintained? ✓
    - Rollback time <5 min? ✓
    
  ✓ Post-deployment:
    - Team notified? ✓
    - Release notes published? ✓
    - Status page updated? ✓
```

### Phase 1 Transition Example

```
Ship Phase 1 (MCP Salesforce integration):

Pre-checks:
  ✓ MCP Salesforce client tested locally
  ✓ Rate limiting strategy validated
  ✓ Data persistence to data/ branch working
  ✓ Dashboard pulling live data (not mocks)
  ✓ No credentials in code

Deployment:
  ✓ GitHub Actions: collect.yml (15-min cron) active
  ✓ First data collection cycle complete
  ✓ data/ branch has timestamp files (2026-08-16/risk_scores.json)
  ✓ GitHub Pages dashboard updated with live data

Monitoring:
  ✓ Workflow history shows 2+ successful runs
  ✓ Data freshness: last update <30 min ago
  ✓ Error rate: 0% (no failed collections)

Rollback:
  ✓ Can revert to Phase 0 mock data in <5 min
  ✓ Git history complete
```

### When to use
- ✅ **Phase 6 START:** Once per phase completion (before release)
- ✅ **Before any production change:** Deployment checklist
- ✅ **After each phase:** Pre-launch validation

### Outputs
- **Pre-deployment checklist:** All green items
- **Deployment validation:** System working
- **Monitoring setup:** Alerts configured
- **Rollback procedure:** Documented and tested
- **Release notes:** Changelog for team

### Benefits
- Production deployments risk-free
- Rollback capability confirmed
- Team confidence high
- Monitoring active from day 1
- Zero-downtime deployments

### Checklist
- [ ] Pre-deployment checklist 100%
- [ ] All tests passing in CI/CD
- [ ] Code review approved
- [ ] Security scan clean
- [ ] Deployment pipeline executes
- [ ] Monitoring alerts active
- [ ] Rollback procedure tested
- [ ] Release notes published
- [ ] Team synchronized

---

## 📊 SKILLS BY PHASE - QUICK REFERENCE

| Phase | Skill | Command | Duration | Frequency |
|-------|-------|---------|----------|-----------|
| 1: SPEC | `/spec` | `/spec` | 2-4 hours | Once/project |
| 2: PLAN | `/plan` | `/plan` | 3-6 hours | Once/phase |
| 3: BUILD | `/build` | `/build` | 8-16 hours | Once/phase |
| 4: TEST | `/test` | `/test` | 6-12 hours | Once/phase |
| 5: REVIEW | `/code-review` | `/code-review medium` | 1-2 hours/PR | Every PR |
| 6: SHIP | `/ship` | `/ship` | 2-4 hours | Once/phase |

---

## 🎯 PHASE WORKFLOW EXAMPLE

### Phase 0 Complete Workflow (3-4 days)

**Day 1: Spec + Plan**
```
/spec                        ← Define Phase 0 requirements (2h)
  → Generates: SPECIFICATION.md (Phases 0-5)
  
/plan                        ← Create Phase 0 roadmap (2h)
  → Generates: PROJECT_ROADMAP_MASTER.md
```

**Day 2: Build**
```
/build                       ← Scaffold Phase 0 (8h)
  → services/collector/, services/heuristic/, services/shared/
  → site/monitoring/ (mock dashboard)
  → .github/workflows/ (test.yml, deploy.yml)
  → Initial tests (stubs)
```

**Day 3: Test**
```
/test                        ← Implement tests (6h)
  → Complete test suite
  → Coverage: 82% backend, 75% frontend
  → All tests passing
```

**Day 3-4: Review**
```
/code-review high            ← Code audit (2-4h)
  → All services reviewed
  → All findings addressed
  → Security validated
```

**Day 4: Ship**
```
/ship                        ← Pre-launch (1-2h)
  → GitHub Pages deploy validated
  → Dashboard live (mock data)
  → Monitoring configured
  → Phase 0 complete ✓
```

---

## 🔗 INTEGRATION WITH PROJECT DOCUMENTATION

- **FRAMEWORK_AGENT_SKILLS_REFERENCE.md:** Agnóstic framework reference (reusable for other projects)
- **SPECIFICATION.md:** Project-specific requirements (Phase 1 output)
- **PROJECT_ROADMAP_MASTER.md:** Project-specific timeline (Phase 2 output)
- **FASE_0_IMPLEMENTATION_GUIDE.md:** Step-by-step Phase 0 execution guide

---

## ✅ SKILLS SETUP CHECKLIST

- [ ] Access to Claude Code confirmed (https://claude.ai/code)
- [ ] `/spec` available and tested
- [ ] `/plan` available and tested
- [ ] `/build` available and tested
- [ ] `/test` available and tested
- [ ] `/code-review` available and tested
- [ ] `/ship` available and tested
- [ ] Team read this document
- [ ] Phase 1 (Spec) can begin

---

**Claude Code Skills are ready. Begin Phase 1: SPECIFICATION.**

