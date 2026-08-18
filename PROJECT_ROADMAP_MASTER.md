# SALESFORCE PREDICTIVE MONITORING - PROJECT ROADMAP
**Status:** ✅ Phases 0-5 delivered — Production monitoring live (GitHub Pages)
**Last Updated:** 2026-08-18
**Total Duration:** 4-5 weeks

---

## 📊 PROJECT PHASES OVERVIEW

```
Phase 0 (3-4 days)    → Phase 1 (5-7 days)    → Phase 2-5 (4-5 weeks)    → Production
├─ Mock Salesforce    ├─ Real Salesforce      ├─ ML Models              ├─ 24/7 Monitoring
├─ Scaffold           ├─ Live Data            ├─ Alerting               ├─ Feedback Loops
├─ Testing            ├─ Persistence          ├─ Dashboard              ├─ Hardening
└─ Zero Dependencies  └─ GitHub Pages         └─ Notifications          └─ Full Prod Stack
```

---

## 🎯 PHASE 0: SCAFFOLD & MOCK (3-4 days)

### Goals
- ✅ 100% functional architecture with zero Salesforce dependency
- ✅ High test coverage (backend ≥80%, frontend ≥70%)
- ✅ Structured logging (JSON Lines)
- ✅ Complete pipeline working end-to-end

### Deliverables
```
services/
├── collector/          # Mock log generator
├── heuristic/          # Risk score calculation
├── comparison/         # Placeholder for ML
└── shared/             # Common utilities

site/
├── monitoring/         # Dashboard (mock data)
├── shared/             # Reusable components
└── styles/             # Tailwind + theme

.github/workflows/
├── test.yml            # Run pytest + Jest
└── deploy.yml          # GitHub Pages — NÃO é workflow: Pages serve direto de `main/docs` (classic Jekyll build), ver `site/scripts/sync-dashboard.mjs`

docs/
├── PHASE_0_IMPLEMENTATION_GUIDE.md
├── TESTING_GUIDE.md
├── SERVICES_CONTRACTS.md
└── ARCHITECTURE.md
```

### Success Criteria
- [x] All tests pass (pytest + Jest)
- [x] Coverage meets minimums (80/70)
- [x] Pipeline runs end-to-end
- [x] Logging validated
- [x] Team can spin up locally in <10 minutes

**Timeline:** Mon-Wed (Mon AM: MCP validation, Mon PM-Tue: scaffold, Tue-Wed: testing)

---

## 🎯 PHASE 1: MCP SALESFORCE INTEGRATION (5-7 days)

### Changes from Phase 0
```python
# Phase 0: Mock
logs = [{"id": "L1", "status_code": 200, ...}]

# Phase 1: Real (2-line change!)
from mcp_salesforce import SalesforceClient
logs = SalesforceClient().query("SELECT * FROM Log__c")
```

### Goals
- ✅ Real Salesforce data via MCP
- ✅ 24/7 GitHub Actions schedule
- ✅ JSON data persisted in `data/` branch
- ✅ Frontend reads live data
- ✅ GitHub Pages deployment active

### Deliverables
```
monitoring/
├── orchestrate.py      # Switched from mock → real
└── salesforce_client.py # MCP wrapper

.github/workflows/
├── collect.yml         # 15-min cron
├── test.yml            # On every commit
└── deploy.yml          # Pages via branch: `main/docs` (sem workflow — clássico)

data/                   # Separate branch
├── 2026-08-18/
│   ├── <stamp>.json    # Snapshot completo (risk_score, alerts, shadow_mode, pipeline)
│   └── <stamp>.prom    # Métricas Prometheus
├── calibration.json    # Auto-calibração (Fase 4)
├── feedback.json       # Feedback do usuário (Fase 4, quando existir)
└── ...

site/
├── api/
│   └── client.js       # Fetch from data/ branch (snapshots por dia + fallback mock)
└── monitoring/
    ├── index.html      # Live dashboard (espelhado em docs/dashboard/ via sync-dashboard.mjs)
    └── dashboard.js    # Render + auto-refresh
```

### Success Criteria
- [x] MCP queries work in GitHub Actions
- [x] Data persisted to `data/` branch
- [x] Dashboard shows live risk_score
- [x] No Salesforce credentials in repo
- [x] 24/7 collection validated (at least 2 cycles)

**Validação em 18/08/2026:** 5 ciclos verdes (3x `workflow_dispatch` + 2x `schedule`) com `SF_REFRESH_TOKEN` rotacionando automaticamente a cada run; snapshots em `data/<dia>/`; dashboard no ar em https://brunotrolo.github.io/Salesforce_PredictiveMonitoring/ lendo os dados reais (HTTP 200 + assets + snapshots verificados).

**Timeline:** Thu-Fri (Thu-Fri early: MCP switch, Fri: validation, Fri PM: GitHub Pages)

---

## 🎯 PHASES 2-5: PRODUCTION FEATURES (4-5 weeks)

### Phase 1 — Auth (RTR) & Kit (18/08/2026 — de hoje)
- **RTR obrigatório descoberto na prática:** tokens de refresh obtidos por PKCE morrem sem renovação (erro no login do app: *"you must contact Support to complete the login"*) — confirmação do suporte Salesforce; não é bug do nosso código, é política de segurança da plataforma.
- **Solução implementada:** rotação automática do `SF_REFRESH_TOKEN` em `collect.yml` (commit `863f401`) — a cada run, troca o refresh token e salva o novo como secret (PAT fine-grained `GH_PAT`). Loop validado com **5 ciclos verdes consecutivos** (timestamps de rotação: 01:25:23Z, 01:35:29Z, 02:06:40Z + schedule 02:35Z).
- **Kit reutilizável publicado:** https://github.com/brunotrolo/Salesforce_MCPauthentication (commit `fc800d3`) — mesmo conteúdo versionado neste repo em `salesforce-mcp-auth-kit/` (README passo a passo, `scripts/get_sf_mcp_tokens.py`, `client/salesforce_mcp_client.py` self-contained, `pipeline/run_with_rotation.py`, `workflow/collect.yml`, `docs/TROUBLESHOOTING.md` com 8 armadilhas reais). Sem secrets no código (validado).

### Phase 2: Alerting & Notifications (1 week)
- ~~Email/Slack notifications on critical alerts~~ (removido por decisão do usuário em 16/08/2026)
- Alert aggregation & deduplication ✅ (16/08/2026 — `services/alerting`, ver SPECIFICATION.md §3.3)
- Severity levels in dashboard ✅ (16/08/2026 — contagens, badge ×N, tag "recorrente")

### Phase 3: ML Shadow Mode (2 weeks)
- ~~Prophet forecasting~~ → regressão linear stdlib (`ForecastEngine`) ✅ (16/08/2026 — `services/ml`, ver SPECIFICATION.md §3.3)
- ~~Isolation Forest anomaly detection~~ → z-score modificado (`AnomalyEngine`) ✅ (16/08/2026 — mediana/MAD, MAD≈0 trata série degenerada)
- Side-by-side comparison (heuristic vs ML) ✅ (16/08/2026 — `ShadowComparator`, shadow = observação, nunca decide)
- A/B testing framework → **fora de escopo** (decisão do usuário em 18/08/2026: shadow mode já compara heurística vs ML sem nunca decidir sozinho; A/B exige tráfego real dividido, que o fluxo atual não tem)

### Phase 4: Feedback Loop (1 week)
- Model accuracy tracking ✅ (16/08/2026 — `AccuracyTracker` em `services/feedback`, ver SPECIFICATION.md §3.3)
- User feedback ingestion ✅ (16/08/2026 — `FeedbackStore` + flag `--feedback-file` no pipeline)
- Weekly retraining pipeline ✅ (16/08/2026 — `Calibrator.recommend` + CLI `python -m feedback.calibrate`; recomendação, nunca aplicação automática)
- Calibração automática no pipeline ✅ (17/08/2026 — `SampleStore` acumula `{threshold, fp_rate}` em `calibration.json` na branch `data`; `--samples-file` + `_run_calibration` antes do shadow; `threshold_used` + `calibration_summary` no snapshot; decisão do usuário em 17/08/2026, ver `docs/FEEDBACK_LOOP_SPEC.md`)
- Wiring do `--feedback-file` no `collect.yml` ✅ (17/08/2026 — baixa `feedback.json` da raiz da branch `data` quando existe)
- Wiring da auto-calibração no `collect.yml` ✅ (17/08/2026 — baixa `calibration.json`, passa `--samples-file`, persiste o arquivo atualizado na raiz da branch `data`)

### Phase 5: Hardening & Scale (1 week)
- Error handling & retries ✅ (17/08/2026 — `services/resilience` (22 testes, 100%) + retry de transporte em `mcp_salesforce.py`; nunca protocolo/4xx)
- Rate limiting & backoff ✅ (17/08/2026 — token bucket com `SF_MAX_QPS` em `mcp_salesforce.py`)
- Sentry error tracking ✅ (17/08/2026 — `init_sentry` opt-in via `SENTRY_DSN`; no-op sem DSN)
- Prometheus metrics ✅ (17/08/2026 — `metrics.py` em text exposition, 100% cobertura; `--metrics-file` no pipeline)
- Production monitoring ✅ (17/08/2026 — hardening do pipeline: passos fatais = collect/analyze/aggregate, observacionais = compare/shadow/accuracy/feedback com `step_errors`; bloco `pipeline` no snapshot; card "Pipeline (último ciclo)" no dashboard; 89 testes monitoring, 91% cobertura)
- Wiring do `--metrics-file`, `SENTRY_DSN` e `--feedback-file` no `collect.yml` ✅ (17/08/2026 — `metrics.prom` persistido na branch `data`, Sentry opt-in via secret, feedback lido da branch `data`)

---

## 🔗 CLAUDE CODE SKILLS & GITHUB PROJECT REFERENCES

### 1️⃣ Claude Code Skills (Recursos Nativos da Plataforma)

**Skills via Slash Commands** (`/comando`):
- ⭐ **`/code-review`** - Revisa código para bugs, performance, test coverage
- ⭐ **`/dataviz`** - Design de visualizações (colors, charts, accessibility, responsiveness)
- ⭐ **`/simplify`** - Refactora código para eliminar duplicação e melhorar eficiência
- ⚠️ **`/loop`** - Executa prompt repetidamente em intervalo (validação Fase 0)
- ⚠️ **`/claude-api`** - Referência Claude API (Fase 5+ apenas)

**→ Ver:** `docs/CLAUDE_CODE_SKILLS.md` (guia completo de uso com exemplos por fase)  
**Acesso:** https://claude.ai/code (web) ou Claude Code Desktop

---

### 2️⃣ GitHub Project References (Dependências Técnicas Externas)

**FASE 0 (Instale Agora):**
- ✅ **Pydantic** (validação JSON) - https://github.com/pydantic/pydantic
- ✅ **structlog** (logging estruturado) - https://github.com/hynek/structlog
- ✅ **pytest** (testes backend) - https://github.com/pytest-dev/pytest
- ✅ **faker** (mock data) - https://github.com/joke2k/faker
- ✅ **Jest** (testes frontend) - https://github.com/jestjs/jest
- ✅ **Tailwind CSS** (styling) - https://github.com/tailwindlabs/tailwindcss
- ✅ **shadcn/ui** (componentes) - https://github.com/shadcn-ui/ui
- ✅ **Black** (code formatter) - https://github.com/psf/black
- ✅ **Ruff** (linter) - https://github.com/astral-sh/ruff
- ✅ **mypy** (type checker) - https://github.com/python/mypy
- ✅ **pre-commit** (git hooks) - https://github.com/pre-commit/pre-commit

**FASE 1 (Adicione):**
- ⚠️ **pandas** (análise de dados) - https://github.com/pandas-dev/pandas
- ⚠️ **factory_boy** (fixtures avançadas) - https://github.com/FactoryBoy/factory_boy
- ⚠️ **Storybook** (dev de componentes) - https://github.com/storybookjs/storybook

**FASE 5+ (Hardening):**
- ⚠️ **Sentry** (error tracking) - https://github.com/getsentry/sentry
- ⚠️ **Prometheus** (métricas) - https://github.com/prometheus/prometheus

**→ Ver:** `docs/GITHUB_PROJECT_REFERENCES.md` (documento completo com detalhes de cada projeto)

---

## 📈 RESOURCE ALLOCATION

| Role | Phase 0 | Phase 1 | Phase 2-5 | Total |
|------|---------|---------|-----------|-------|
| Backend Engineer | 4 days | 3 days | 2 wks | 3 wks |
| Frontend Engineer | 2 days | 2 days | 1.5 wks | 2 wks |
| DevOps/SRE | 1 day | 1 day | 0.5 wk | 1 wk |
| **Team Total** | **1 wk** | **1 wk** | **4-5 wks** | **5-6 wks** |

**Nota:** Inclui ~6-8 horas extras de setup das GitHub Skills em Fase 0

---

## 💰 COST ANALYSIS

| Component | Cost | Notes |
|-----------|------|-------|
| GitHub Actions | $0 | Public repo, unlimited minutes |
| GitHub Pages | $0 | Included with free tier |
| Salesforce API | $0 | Existing subscription |
| MCP (Claude Session) | $0 | Included with Claude subscription |
| Infrastructure | $0 | Everything in git/Actions |
| **TOTAL** | **$0/month** | Zero incremental cost |

---

## 🏗️ ARCHITECTURE SUMMARY

```
┌─────────────────────────────────────────────────────────────────┐
│                      PHASE 0-5 ARCHITECTURE                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────┐        ┌──────────────────────┐
│   Salesforce API    │        │  GitHub Actions      │
│   (via MCP)         │◄──────►│  (Orchestration)     │
└─────────────────────┘        └──────────────────────┘
         ▲                              │
         │                              ▼
         │                      ┌──────────────────┐
         │                      │ services/        │
         │                      │ ├─ collector     │
         │                      │ ├─ heuristic     │
         │                      │ ├─ comparison    │
         │                      │ └─ shared/       │
         │                      └──────────────────┘
         │                              │
         │                              ▼
         │                      ┌──────────────────┐
         │                      │ JSON Output      │
         │                      │ (risk scores,    │
         │                      │  alerts)         │
         │                      └──────────────────┘
         │                              │
         │                              ▼
         │                      ┌──────────────────┐
         │                      │ data/ branch     │
         │                      │ (persistence)    │
         │                      └──────────────────┘
         │                              │
         │                              ▼
         │                      ┌──────────────────┐
         │                      │ site/            │
         │                      │ (monitoring UI)  │
         │                      │ GitHub Pages     │
         │                      └──────────────────┘
```

---

## 📋 QUICK REFERENCE: CRITICAL FILES

### Phase 0 Scaffolding
```
docs/FASE_0_IMPLEMENTATION_GUIDE.md    ← START HERE
ARCHITECTURE.md                         ← High-level design
PREDICTIVE_MONITORING_PLAN.md           ← Original spec
```

### Phase 0 Development
```
services/collector/src/collector.py      ← Mock log generator
services/heuristic/src/heuristic.py      ← Risk score logic
services/shared/src/logger.py            ← JSON logging
monitoring/orchestrate.py                ← Pipeline orchestrator
```

### Testing
```
services/*/tests/conftest.py             ← Fixtures
services/*/tests/fixtures/mock_*.yaml    ← Test data
site/monitoring/tests/test-dashboard.js  ← Frontend tests
```

### Phase 1 Transition
```
monitoring/salesforce_client.py          ← MCP wrapper (NEW)
.github/workflows/collect.yml            ← 15-min schedule (NEW)
site/api/client.js                       ← API fetcher (MODIFIED)
```

---

## ⚙️ TECHNOLOGY STACK

### Backend
- **Language:** Python 3.10+
- **Testing:** pytest + pytest-cov
- **Data Validation:** Pydantic
- **Logging:** structlog (JSON Lines)
- **Data Processing:** pandas
- **ML (Phase 3):** stdlib puro (regressão linear + z-score modificado); Prophet/sklearn plugáveis pela interface (`docs/ML_SHADOW_MODE_SPEC.md`)

### Frontend
- **Framework:** Vanilla JS (no build required)
- **Testing:** Jest
- **Styling:** Tailwind CSS
- **Components:** shadcn/ui patterns

### DevOps
- **CI/CD:** GitHub Actions
- **Deployment:** GitHub Pages
- **Data Store:** Git (data/ branch)
- **Scheduling:** GitHub Actions cron

### Salesforce Integration
- **Method:** Model Context Protocol (MCP)
- **Authentication:** Managed by MCP
- **Rate Limiting:** MCP built-in
- **Error Handling:** Retry logic in MCP

---

## 🔐 SECURITY & COMPLIANCE

### Secrets Management
- [ ] No Salesforce tokens in code
- [ ] MCP handles authentication
- [ ] GitHub Secrets for env vars (if needed)
- [ ] Audit log all queries (Phase 2+)

### Data Privacy
- [ ] PII redacted in logs (Phase 1+)
- [ ] No sensitive data in git history
- [ ] Data retention policy (Phase 2+)

### Access Control
- [ ] Admin: GitHub repo settings
- [ ] Monitors: GitHub Pages viewer
- [ ] Developers: PR-based workflow

---

## 🚨 RISK MITIGATION

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| MCP fails in Actions | Medium | High | Test in Phase 0, switch to API if needed |
| GitHub API limits | Low | Medium | Batch queries, cache data |
| Data growth explodes | Low | Medium | Squash data/ branch monthly |
| Model accuracy bad | Medium | Medium | Shadow mode tracking + accuracy feedback loop (Fase 4); A/B abandonado — fora de escopo |
| Salesforce SLA breach | Low | High | Alert escalation (Phase 2) |

---

## 📞 ESCALATION CONTACTS

- **Technical Lead:** @brunotrolo
- **Backend:** [Assign engineer]
- **Frontend:** [Assign engineer]
- **DevOps:** [Assign SRE]

---

## ✅ CHECKLIST: BEFORE STARTING PHASE 0

- [ ] Team read ARCHITECTURE.md
- [ ] Team has access to Salesforce API docs
- [ ] Python 3.10+ installed locally
- [ ] Node 18+ installed locally
- [ ] Git credentials configured
- [ ] GitHub repo cloned
- [ ] Assigned roles: Backend, Frontend, DevOps
- [ ] MCP Salesforce validation scheduled

**Ready to kickoff? → Start `docs/FASE_0_IMPLEMENTATION_GUIDE.md` (Step 1)**

---

## 📝 CHANGE LOG

| Date | Change | Author |
|------|--------|--------|
| 2026-08-15 | Initial roadmap + Phase 0-1 detailed | @claude-code |
| 2026-08-15 | Architecture validation complete | @claude-code |
| 2026-08-16 | Phases 2-5 delivered (alerting, ML shadow, feedback loop) | @claude-code |
| 2026-08-17 | Phase 4-5 wiring (auto-calibração, metrics, Sentry, feedback no collect.yml) | @claude-code |
| 2026-08-18 | Phase 1 closed: auth RTR resolvido (rotação automática do secret), 5 ciclos verdes, kit publicado (`salesforce-mcp-auth-kit/` + repo `Salesforce_MCPauthentication`), GitHub Pages live validado, success criteria da Phase 1 marcados | @opencode |
| 2026-08-18 | Dashboard v2 na raiz do Pages: página única e explicada em `https://brunotrolo.github.io/Salesforce_PredictiveMonitoring/` (fonte da verdade em `site/monitoring/`, espelho gerado para `docs/`), painel de diagnóstico com "Copiar diagnóstico", coleta de 15 → 5 min (`collect.yml`), A/B testing fora de escopo (decisão do usuário) | @opencode |

---

**Last reviewed:** 2026-08-18
**Next review:** —

---

**Project Status:** ✅ PRODUCTION — 24/7 monitoring live (Pages), Phases 0-5 delivered, auth com rotação automática do secret.

Start Phase 0 immediately. Follow `docs/FASE_0_IMPLEMENTATION_GUIDE.md` for step-by-step instructions.

Questions? Create an Issue or discuss with @brunotrolo.
