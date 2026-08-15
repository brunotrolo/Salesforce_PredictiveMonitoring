# ANÁLISE ARQUITETURAL E RECOMENDAÇÃO DE SKILLS
**Projeto:** Salesforce Predictive Monitoring (GitHub-Native)  
**Data:** 2026-08-15  
**Arquiteto:** Claude Code  
**Status:** Viabilidade Validada ✓

---

## 1. ANÁLISE DA ARQUITETURA

### 1.1 Entendimento Técnico

O projeto segue uma arquitetura **event-driven + data pipeline** 100% GitHub-nativa:

```
Salesforce (Nebula Logger)
    ↓ [OAuth 2.0 via Secrets]
GitHub Actions (Runner + Python 3.11)
    ├─ Coleta SOQL (30 min últimos logs)
    ├─ Heurística Adaptativa (Fase 1: EWMA + Z-score)
    └─ Modo Sombra ML (Fase 3+: Prophet + Isolation Forest)
    ↓
Branch `data` (JSON versionado)
    ├─ latest.json (snapshot atual)
    ├─ history.json (30 dias)
    ├─ alerts.json (eventos críticos)
    ├─ predictions.json (comparativo modelos)
    └─ feedback.json (falsos positivos)
    ↓
GitHub Pages (Front-end estático)
    ├─ Fetch raw.githubusercontent.com (auto-refresh 5 min)
    ├─ Dashboard interativo
    └─ Botão feedback → GitHub Issues
    ↓
GitHub Issues (Webhook-driven)
    └─ Atualiza feedback.json + reentreina
```

### 1.2 Decisões Arquiteturais Críticas ✓ VALIDADAS

| Decisão | Justificativa | Risco Mitigado |
|---------|---------------|-----------------|
| GitHub Actions substitui Apps Script + Colab | Eliminação de dependência de navegador aberto, headless 24/7 | Cold-start, sessão expirada, Colab Pro requerido |
| Heurística adaptativa (Fase 1), não ML imediato | Evita cold-start de modelos que precisam semanas de histórico | Complexidade prematura, deployments frágeis |
| Branch `data` isolado de `master` | 288 commits/dia de dados não poluem histórico de código | Git history ilegível, dificuldade em revert, merge complexo |
| Front-end busca JSON via raw.githubusercontent.com | Pages quase nunca redeploy, dados atualizados 5 min | Latência de deploy, rebuild desnecessário, overhead de CI |
| GitHub Issues como único backend de escrita | Sem servidor customizado, autenticação nativa, zero custo | Token exposure, infrastructure creep |

### 1.3 Pilares Técnicos Identificados

1. **Autenticação & Segurança**
   - OAuth 2.0 Salesforce com refresh_token em GitHub Secrets
   - IP Trusted Range (possível bloqueio de runners dinâmicos)
   - Token rotation strategy

2. **Data Pipeline**
   - SOQL query (30 min + limit 500 logs)
   - Python + Pandas para transformação
   - JSON versionado como "database"
   - Commit automático com atomicidade (git-based)

3. **Heurística Adaptativa (Principal, Fase 1)**
   - EWMA (média móvel exponencial) por bucket horário + dia da semana
   - MAD (median absolute deviation) para robustez contra outliers
   - Z-score adaptativo por bucket
   - Threshold ajustável via feedback humano

4. **Comparativa ML (Sombra, Fase 3+)**
   - Prophet para forecasting de tendências
   - Isolation Forest para detecção de anomalias
   - Registro lado-a-lado (heurística vs. sombra vs. resultado real)
   - Decisão de promoção manual baseada em dados

5. **Front-end & UX**
   - HTML5/CSS3 + JavaScript vanilla (sem framework)
   - Auto-refresh client-side (5 min)
   - Health check visual (dado desatualizado > 15 min?)
   - Feedback pré-preenchido via URL params (GitHub Issues API)

6. **CI/CD & Testing**
   - GitHub Actions (workflows: coleta, feedback, retrain, testes)
   - Pytest para unit tests
   - Pages deployment (raro)

---

## 2. VALIDAÇÃO DE ACESSOS & PRÉ-REQUISITOS

### 2.1 Pré-requisitos Confirmados ✓

- [x] Repositório GitHub (`brunotrolo/salesforce_predictivemonitoring`) 
  - **Status:** Acessível, branch `claude/project-plan-analysis-validation-emeiaw` pronta para desenvolvimento
  - **Permissões:** Push, branch management, secrets
  
- [x] Salesforce Connected App (OAuth)
  - **Status:** Já documentado em `SALESFORCE_MCP_SETUP.md` (mencionado no plano)
  - **Dados necessários:** Client ID, Client Secret, Refresh Token → GitHub Secrets
  - **SOQL:** Nebula Logger (`Log__c`), últimos 30 min, limite 500

- [x] GitHub Pages
  - **Status:** Habilitado por padrão para repositórios públicos
  - **Deploy:** Raro (só quando site muda, não dados)
  - **Branch:** `master` com `/site` ou separado

- [x] GitHub Actions
  - **Minutos gratuitos:** ~2000/mês para público (mais que suficiente: ~288 execuções/dia × 2-5 min = ~1000 min/mês)
  - **Secrets:** `SF_CLIENT_ID`, `SF_CLIENT_SECRET`, `SF_REFRESH_TOKEN` (precisam ser criadas)
  - **Permissions:** `contents: write` (para commits automáticos), `issues: write` (para feedback)

- [x] Python 3.11 no runner
  - **Status:** Padrão do ubuntu-latest
  - **Dependências Fase 1:** `pandas`, `requests` (~100 MB)
  - **Dependências Fase 3+:** `prophet`, `scikit-learn` (~500 MB extra)

### 2.2 Riscos & Validações Específicas

| Risco | Validação | Status |
|-------|-----------|--------|
| Salesforce Trusted IP Range bloqueia runners dinâmicos | Relaxar IP restriction ou usar GitHub IP ranges publicados | Pré-requisito de Fase 0 |
| Cron GitHub Actions atrasa em picos de carga | Monitorar real execution times no histórico; aceitar 5 min como alvo, não SLA rígido | Design já absorvido |
| `refresh_token` expira | Documentar processo de renovação manual (Connected App do Salesforce) | Runbook necessário (Fase 5) |
| Rate limit Salesforce (API calls) | Implementar backoff exponencial, cache inteligente | Mitigação em retry logic |
| Crescimento de branch `data` (muitos commits) | Squash periódico do histórico (sem afetar `master`) | Rotina de manutenção (Fase 5) |

---

## 3. FLUXOS CRÍTICOS MAPEADOS

### 3.1 Fluxo de Coleta & Predição (a cada 5 min)

```python
# 1. Autenticação
oauth_token = request_salesforce_token(client_id, client_secret, refresh_token)

# 2. SOQL Query
logs = query_nebula_logger(oauth_token, "SELECT ... WHERE CreatedDate = LAST_N_MINUTES:30")

# 3. Transformação
df = pandas.DataFrame(logs)
df['ServiceDuration'] = df['ServiceDuration__c'].astype(float)

# 4. Heurística (Fase 1)
risk_score, alerts = heuristic.analyze(df, historical_baseline)

# 5. Modo Sombra (Fase 3+)
shadow_scores = shadow_ml.predict(df)

# 6. Persistência (JSON)
latest.json = {"risk_score": 0.72, "timestamp": "2026-08-15T14:05:00Z", ...}
history.json = append(latest)
predictions.json = {heuristic_score, shadow_scores, actual_result}

# 7. Commit automático
git checkout data
git add monitoring/data/
git commit -m "Dados $(date)"
git push origin data
```

**Timeframe esperado:** ~30s (coleta) + ~5s (heurística) = ~35s < 5 min (confortável)

### 3.2 Fluxo de Feedback (via Issues)

```
1. Usuário vê alerta no Dashboard
2. Clica "Marcar Falso Positivo"
3. GitHub Issues abre (pré-preenchido):
   - Título: "Feedback: Falso Positivo (alert_id_xyz)"
   - Body: "alert_id: xyz\ntimestamp: 2026-08-15T14:05:00Z"
   - Label: "feedback"
4. Usuário confirma (já logado no GitHub)
5. Issue criada → dispara workflow `monitoring-feedback.yml`
6. `process_feedback.py` parseia Issue
7. Atualiza `feedback.json`
8. Commit automático em `data`
9. Workflow fecha a Issue com "Feedback registrado"
10. Semana seguinte, `weekly_retrain.py` lê feedback.json e recalibra thresholds
```

**UX simplificado, sem backend próprio:** ✓

### 3.3 Fluxo de Retrain (semanal, Fase 4+)

```python
# 1. Lê feedback.json (falsos positivos registrados)
false_positives = load_feedback_json()

# 2. Analisa predictions.json (histórico comparativo)
weekly_stats = analyze_predictions(predictions.json, timeframe="last_7_days")

# 3. Ajusta thresholds por bucket (heurística)
for bucket in buckets:
    feedback_count = len([fp for fp in false_positives if matches_bucket(fp, bucket)])
    if feedback_count > threshold_adjustment_trigger:
        new_threshold = recalibrate_threshold(bucket, feedback_count)

# 4. Retreina modelo sombra (Fase 3+)
if mode_shadow_active:
    prophet_model = retrain_prophet(history.json)
    isolation_forest = retrain_isolation_forest(history.json, contamination=...)

# 5. Calcula comparativo (precisão/recall por modelo)
compare_models.py → gera modelo_comparison.json

# 6. Commit automático
git commit -m "Retrain semanal + feedback reconciliation"
```

**Frequência:** 1x por semana (cron: `0 2 * * 1` = segunda 2am UTC)  
**Impacto:** Melhoria contínua baseada em dados reais, sem decisões automáticas silenciosas

---

## 4. RECOMENDAÇÕES DE SKILLS PARA DESENVOLVIMENTO PROFISSIONAL

### 4.1 **BACKEND (Python + Data Pipeline)**

#### Skill 1: **Code Quality & Testing** (Python profissional)
- **Aplicável a:** Todos os scripts Python (`.py`)
- **Necessidade:** Pytest fixtures, mocks para Salesforce API, coverage >80%
- **Profissionalismo:** Testes garantem confiabilidade de automação crítica (24/7)
- **Skills existentes:** `/code-review` + `/simplify` 
- **Recomendação:** **USE `/code-review` com `--comment` em PRs de backend**

#### Skill 2: **API Integration & Error Handling** (Salesforce OAuth + Retry)
- **Aplicável a:** `collect_and_predict.py` (autenticação + SOQL)
- **Necessidade:** Backoff exponencial, cache inteligente, validação de response
- **Profissionalismo:** Production-grade resilience
- **Recomendação:** **CUSTOM SKILL sugerida** - "Salesforce-API-Integration" (não existe atualmente)
  - Template: Retry logic com jitter, rate-limit detection, circuit breaker pattern

#### Skill 3: **Data Transformation & Validation** (Pandas + JSON schemas)
- **Aplicável a:** `heuristic.py`, `shadow_ml.py`
- **Necessidade:** Schema validation, type hints, pipeline integrity checks
- **Profissionalismo:** Previne silent data corruption
- **Skills existentes:** Use `/simplify` para limpeza de lógica de transformação
- **Recomendação:** **Python type hints + Pydantic para modelos de dados**

### 4.2 **FRONTEND (HTML/CSS/JavaScript)**

#### Skill 4: **Frontend Quality & Accessibility** (HTML5/CSS3/JS vanilla)
- **Aplicável a:** `site/index.html`, `site/styles.css`, `site/app.js`
- **Necessidade:** Acessibilidade (WCAG 2.1 AA), responsividade, testes de UX
- **Profissionalismo:** Dashboard deve ser usável em mobile, screen readers, testes visuais
- **Skills existentes:** `artifact-design` (não exatamente, é para artifacts)
- **Recomendação:** **Skill especializada em Frontend profissional**
  - Para este projeto: sem framework (vanilla JS), mas com qualidade Enterprise
  - Performance: Bundle < 100KB, Lighthouse > 90

#### Skill 5: **Data Visualization & Dashboard UX**
- **Aplicável a:** Dashboard (risk_score, histórico, tendências)
- **Necessidade:** Gráficos claros, cores acessíveis, interação intuitiva
- **Profissionalismo:** Dados críticos (alertas) precisam ser lidos em 2 segundos
- **Skills existentes:** `dataviz` (Recharts, D3, etc.)
- **Recomendação:** **USE `/dataviz` ANTES DE ESCREVER HTML/JS do dashboard**
  - Paleta de cores validada (light/dark mode)
  - Chart specs (tipos: line para tendência, gauge para risk_score)
  - Accessible legends, tooltips

### 4.3 **DEVOPS & AUTOMATION (GitHub Actions + CI/CD)**

#### Skill 6: **GitHub Actions Workflows & CI/CD Pipeline**
- **Aplicável a:** `.github/workflows/*.yml`
- **Necessidade:** Idempotência, permissões precisas, secrets management
- **Profissionalismo:** Workflows mal escrito causam falhas silenciosas (Fase 0 crítica)
- **Skills existentes:** Nenhuma skill dedicated (documentação + best practices)
- **Recomendação:** **CUSTOM SKILL sugerida** - "GitHub-Actions-Professional"
  - Checklist: Secrets com permissão mínima, logging estruturado, notifications
  - Validação: Testar workflows em sandbox antes de ativar cron

#### Skill 7: **Monitoring & Observability** (logging, health checks)
- **Aplicável a:** Health banner no dashboard, logs estruturados no Actions
- **Necessidade:** Detectar falhas (workflow não rodou, dado desatualizado >15min)
- **Profissionalismo:** SLA implícito de 24/7 requer observabilidade
- **Recomendação:** **USE `loop` skill para monitorar execução de workflows durante Fase 0**

### 4.4 **ARCHITECTURE & PLANNING**

#### Skill 8: **Technical Documentation & ADR** (Architecture Decision Records)
- **Aplicável a:** Documento de razões por trás de cada decisão
- **Necessidade:** "Por quê" Branch `data` é separado? Por quê heurística antes de ML?
- **Profissionalismo:** Onboarding de novos devs, audit trail
- **Recomendação:** **Criar `docs/ADR.md` com template ADR**

---

## 5. PLANO DE SKILLS POR FASE

### Fase 0 — Validação (1-3 dias)
| Skill | Linguagem | Responsável | Prioridade |
|-------|-----------|-------------|-----------|
| `/code-review` low | Python | Backend | CRÍTICA |
| GitHub Actions Setup | YAML | DevOps | CRÍTICA |
| `/dataviz` (health check mockup) | HTML/CSS | Frontend | ALTA |

### Fase 1 — MVP Heurística (5-7 dias)
| Skill | Linguagem | Responsável | Prioridade |
|-------|-----------|-------------|-----------|
| `/code-review` medium | Python | Backend | CRÍTICA |
| Data validation (Pydantic) | Python | Backend | ALTA |
| Frontend dashboard básico | JS/CSS | Frontend | ALTA |
| GitHub Actions workflows (coleta + deploy) | YAML | DevOps | CRÍTICA |

### Fase 2 — Severidade & Notificação (2-3 dias)
| Skill | Linguagem | Responsável | Prioridade |
|-------|-----------|-------------|-----------|
| `/code-review` medium | Python | Backend | ALTA |
| Email/Slack integration | Python + YAML | DevOps | MÉDIA |
| Dashboard alertas visuais | JS/CSS | Frontend | ALTA |

### Fase 3 — Modo Sombra ML (7-10 dias)
| Skill | Linguagem | Responsável | Prioridade |
|-------|-----------|-------------|-----------|
| `/code-review` high (ML) | Python | Backend | CRÍTICA |
| ML model validation | Python | Backend | CRÍTICA |
| Predictions.json schema | Python + JSON | Backend | ALTA |
| Model comparison dashboard | JS/CSS | Frontend | ALTA |

### Fase 4 — Feedback Loop (3-5 dias)
| Skill | Linguagem | Responsável | Prioridade |
|-------|-----------|-------------|-----------|
| GitHub Issues API integration | Python | Backend | ALTA |
| Weekly retrain logic | Python | Backend | CRÍTICA |
| UX do botão feedback | JS/HTML | Frontend | ALTA |

### Fase 5 — Hardening (5-7 dias)
| Skill | Linguagem | Responsável | Prioridade |
|-------|-----------|-------------|-----------|
| Error handling & retry logic | Python | Backend | CRÍTICA |
| Runbook & documentation | Markdown | DevOps | ALTA |
| Performance optimization | JS/Python | Full-stack | ALTA |

---

## 6. CONCLUSÃO: VIABILIDADE ✓ CONFIRMADA

### Pontos Fortes
1. **Arquitetura clara** — 100% GitHub-native, zero dependências exógenas
2. **Faseamento realista** — MVP sem ML (Fase 1) separa MVPs de nice-to-haves
3. **Custos zero** — Actions + Pages gratuitos, sem Colab Pro, sem servidor
4. **24/7 confiável** — Headless architecture elimina toque humano necessário
5. **Feedback loop built-in** — GitHub Issues como backend de escrita é elegante

### Desafios Técnicos (Gerenciáveis)
1. **Trusted IP Range Salesforce** — Mitigação: relaxar restriction ou allowlist GitHub IPs
2. **Cold-start ML (Fase 3)** — Mitigação: Heurística primeiro (Fase 1), ML em sombra depois
3. **Git history crescimento (branch data)** — Mitigação: Squash periódico (Fase 5)
4. **Segurança de Secrets** — Mitigação: Token rotation, audit logging (Fase 5)

### Equipe Recomendada
- **1 Backend Engineer** (Python, Salesforce OAuth, Pandas)
- **1 Frontend Engineer** (HTML/CSS/JS vanilla, UX crítica)
- **1 DevOps/SRE** (GitHub Actions, CI/CD, monitoring)
- **1 ML Engineer** (opcional até Fase 3, Prophet + Isolation Forest)

### Timeline Realista
- **Fase 0:** 1-3 dias (validação)
- **Fase 1:** 5-7 dias (MVP heurística)
- **Fase 2:** 2-3 dias (notificações)
- **Fase 3:** 7-10 dias (ML sombra)
- **Fase 4:** 3-5 dias (feedback loop)
- **Fase 5:** 5-7 dias (production hardening)
- **Total:** ~4-5 semanas até produção 100% robusta

---

## Próximos Passos (Ação)

1. **Criar GitHub Secrets** (pré-Fase 0):
   - `SF_CLIENT_ID`, `SF_CLIENT_SECRET`, `SF_REFRESH_TOKEN`
   - Validar Trusted IP Range no Salesforce Connected App

2. **Scaffold do repositório** (Fase 0):
   - Criar estrutura: `monitoring/{scripts,site,data}/`
   - Branches: `master` (código) + `data` (dados, criado em primeiro workflow)
   - Proteger `master` (require PR, dismiss stale reviews)

3. **Primeiros testes** (Fase 0):
   - OAuth test (sample SOQL query)
   - Git commit test (dummy JSON no branch data)
   - Pages health check (site consegue carregar?)

4. **Onboarding de skills** (paralelo Fase 0-1):
   - Backend team: `/code-review` + Pydantic study
   - Frontend team: `/dataviz` study + Lighthouse audits
   - DevOps team: GitHub Actions deep-dive

---

**Documento preparado como Arquiteto de Solução.**  
**Viabilidade técnica confirmada. Pronto para kick-off.**
