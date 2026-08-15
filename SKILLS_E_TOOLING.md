# GUIA DEFINITIVO DE SKILLS E TOOLING
**Projeto:** Salesforce Predictive Monitoring  
**Propósito:** Desenvolvimento profissional de Backend + Frontend + DevOps  
**Data:** 2026-08-15

---

## PARTE 1: SKILLS DISPONÍVEIS E APLICABILIDADE

### 1. BACKEND PYTHON

#### Skill: `/code-review` 
**Quando usar:** Antes de fazer merge de ANY PR de Python  
**Exemplos de uso:**
```bash
/code-review                    # Revisa diff atual (Fase 1: heuristic.py)
/code-review --comment          # Posta findings como comentários inline no PR
/code-review medium             # Esforço médio (balanceado)
/code-review high               # Full analysis (ML models, Fase 3+)
```

**O que valida:**
- Correctness bugs (typos, logic errors)
- Simplification (DRY, premature abstractions)
- Efficiency (O(n) vs O(n²), unnecessary loops)
- Test coverage (pytest assertions, mocks)

**Fase aplicável:**
- Fase 1: LOW effort (heuristic.py é simples, EWMA + z-score)
- Fase 2: LOW effort (notification logic é straightforward)
- Fase 3: HIGH effort (Prophet + Isolation Forest é complex)
- Fase 4: MEDIUM effort (feedback loop logic)

**Não valida:** Architecture decisions, design patterns (use `/simplify` para isso)

---

#### Skill: `/simplify` 
**Quando usar:** Para limpar código repetitivo ANTES de escrever novo  
**Exemplos de uso:**
```bash
/simplify                       # Refatora diff atual
```

**Aplicabilidade:**
- Transformação de dados (pandas operations em heuristic.py)
- Modelo de dados (reduzir número de JSONs? Consolidar schema?)
- Pipeline (coleta → transformação → persistência pode ser classe reutilizável?)

**Fase aplicável:**
- Fase 1: SIM (antes de escrever collect_and_predict.py)
- Fase 3: SIM (antes de modo sombra — evita código duplicado)
- Fase 4: SIM (lógica de retrain pode ficar elegante)

---

#### Skill: `/claude-api` 
**Quando usar:** Quando precisar de referência sobre Claude API/Models  
**Não aplicável:** Neste projeto não usamos LLM no backend, então skill raramente necessária
**Exceção:** Se em Fase 5+ decidirmos usar Claude para análise inteligente de patterns, voltamos aqui

---

### 2. FRONTEND JAVASCRIPT/HTML/CSS

#### Skill: `/dataviz` 
**CRÍTICA para este projeto** — Dashboard é interface crítica  
**Quando usar:** ANTES DE ESCREVER `site/app.js` e `site/styles.css`  
**O que entrega:**
- Paleta de cores validada (light/dark mode compatível)
- Chart type selection (line, gauge, bar)
- Acessibilidade checklist (WCAG 2.1)
- Responsive design foundation
- Color contrast validation

**Fases aplicáveis:**
- Fase 0-1: SIM (mock do dashboard com risk_score gauge)
- Fase 2: SIM (alertas com severidade cores)
- Fase 3: SIM (gráficos comparativos heurística vs. sombra)
- Fase 4: SIM (feedback UX refinement)

**Exemplo de uso:**
```bash
/dataviz
```
Input: Descrição dos componentes (risk gauge 0-1, line chart 30 dias, status badges)  
Output: Paleta, chart specs, Tailwind classes (ou CSS vanilla), accessibility notes

**Deliverables esperados:**
- `references/palette.md` (cores validadas)
- Recomendações de tipos de chart
- Layout grid + responsive breakpoints
- Accessibility checklist (labels, ARIA, focus management)

---

#### Skill: `artifact-design` 
**Quando usar:** Quando criamos artifacts (mockups, documentação visual)  
**Aplicabilidade BAIXA:** Neste projeto o frontend é parte do repo, não artifact  
**Exceção:** Se criarmos mockups interativos para validação, recomendação neste projeto seria usar artifact-design antes

**Não recomendado para:** Código real do site (use /dataviz)

---

### 3. DEVOPS & CI/CD

#### Skill: `session-start-hook` 
**Quando usar:** Configurar hooks para Claude Code Web sessions  
**Aplicabilidade MÉDIA:** Se desenvolver em web e precisar que testes rodem automaticamente  
**Recomendação:** Use para garantir que pytest roda no `monitoring-tests.yml` antes de qualquer merge

---

#### Skill: `loop` 
**Quando usar:** Para monitoramento contínuo durante desenvolvimento  
**Fase aplicável:**
- Fase 0: SIM (monitorar execução do primeiro workflow)
  ```bash
  /loop 5m /status    # Verifica a cada 5 min se workflow rodou
  ```
- Fase 1: SIM (validar que coleta roda corretamente por 1 hora)
- Fase 2+: NÃO necessário (confiança estabelecida)

**Uso específico:**
```bash
/loop 5m 
  Verifique se o último workflow `monitoring-collect.yml` rodou com sucesso
  e se branch `data` tem commit recente (últimos 10 minutos)
```

---

### 4. DOCUMENTAÇÃO & ARQUITETURA

#### Skill: Nenhuma skill específica
**Recomendação:** Use padrão ADR (Architecture Decision Record)  
**Onde:** `docs/ADR.md` com template:
```markdown
# ADR-001: Por que Branch `data` é separado de `master`

## Context
Workflow roda a cada 5 minutos = 288 commits/dia

## Decision
Usar branch `data` isolado para persistência

## Consequences
- Pros: Histórico de código limpo
- Cons: Workflow mais complexo (git checkout data)

## Alternatives Considered
1. Squash commits automaticamente (frágil)
2. Usar database externa (violaria zero-cost principle)
```

---

## PARTE 2: MCP SERVERS & INTEGRAÇÃO

### 1. Salesforce MCP (SalesforceRead)
**Status:** Disponível nesta sessão  
**Uso:** Validação de conectividade em Fase 0  
**Não recomendado para:** Backend script (use `requests` + OAuth direto)  
**Razão:** MCP é feito para agentes (Claude), não automação headless

**Quando usar:**
- Fase 0: Validar que OAuth funciona
  ```python
  # Em vez de: requests + manual OAuth
  # Use MCP: query via SalesforceRead.soqlQuery
  ```

---

### 2. GitHub MCP (github)
**Status:** Disponível nesta sessão  
**Aplicação:**
- Criar workflows via API (não manual)
- Listar issues de feedback
- Validar branch proteções
- Monitorar execução de Actions

**Não recomendado para:** Commit automático (use Git direto no workflow Python)

---

### 3. Google Sheets MCP (GoogleSheetsMCP)
**Status:** Disponível  
**Aplicabilidade:** NENHUMA — Projeto é 100% GitHub, zero Google Sheets  
**Nota:** Plano v1 usava Sheets; v2 substituiu por JSON versionado no git

---

## PARTE 3: SKILL ROADMAP POR TIMING

### ANTES DO KICK-OFF (Preparação)
- [ ] ler `/dataviz` e criar `references/palette.md`
- [ ] ler `/code-review` para entender linhas vermelhas de review
- [ ] Estudar GitHub Actions best practices (docs, não skill específica)
- [ ] Validar Secrets do Salesforce no GitHub

### FASE 0 (Dias 1-3)
**Backend:**
- [ ] `/code-review low` no `collect_and_predict.py` (stub)
- [ ] Criar `monitoring/scripts/requirements.txt` (pandas, requests)
- [ ] Teste OAuth via SalesforceRead MCP

**Frontend:**
- [ ] `/dataviz` mockup dashboard (gauge risk_score + status)
- [ ] Criar `site/styles.css` base com paleta validada

**DevOps:**
- [ ] Criar `.github/workflows/monitoring-collect.yml`
- [ ] Validar branch `data` criado em primeiro run
- [ ] `/loop` monitor por 1 hora

### FASE 1 (Dias 4-10)
**Backend:**
- [ ] `/code-review medium` em `heuristic.py`
- [ ] `/simplify` se houver transformações Pandas repetidas
- [ ] Implementar EWMA + z-score + MAD

**Frontend:**
- [ ] `/dataviz` validação de cores em risk_score gauge
- [ ] Implementar `app.js` com fetch() + auto-refresh

**DevOps:**
- [ ] Setup GitHub Pages (`site/` → public)
- [ ] Health check banner (timestamp > 15 min?)

### FASE 2 (Dias 11-13)
**Backend:**
- [ ] Integração com Slack/Email (webhook curl)
- [ ] `/code-review medium`

**Frontend:**
- [ ] `/dataviz` badges de severidade (CRÍTICA/ALTA/MÉDIA/BAIXA)
- [ ] Alertas visuais no dashboard

### FASE 3 (Dias 14-23)
**Backend:**
- [ ] `/code-review high` em `shadow_ml.py` (Prophet + Isolation Forest)
- [ ] Validar schemas `predictions.json`
- [ ] Implementar `compare_models.py`

**Frontend:**
- [ ] `/dataviz` line charts (heurística vs. sombra vs. real)
- [ ] Tabelas de precisão/recall

### FASE 4 (Dias 24-28)
**Backend:**
- [ ] Integração GitHub Issues API (`process_feedback.py`)
- [ ] `/code-review medium` em weekly_retrain.py

**Frontend:**
- [ ] Botão feedback com URL pré-preenchida
- [ ] UX refinement

### FASE 5 (Dias 29-35)
**Backend:**
- [ ] `/code-review high` em error handling + retry logic
- [ ] `/simplify` cleanup geral

**DevOps:**
- [ ] Runbook + troubleshooting docs
- [ ] Branch `data` squash automático

---

## PARTE 4: CHECKLIST DE QUALIDADE POR SKILL

### Code Review Checklist (`/code-review`)
```markdown
- [ ] Tipos Python definidos (type hints em function signatures)
- [ ] Sem variáveis `_unused` ou código morto
- [ ] Logs estruturados (não print())
- [ ] Exceções tratadas (não bare `except`)
- [ ] Nenhuma hardcoded secret ou IP
- [ ] Testes unitários para lógica crítica
- [ ] Docstrings (1 linha, não multi-paragraph)
```

### DataViz Checklist (`/dataviz`)
```markdown
- [ ] Paleta de cores validada em light/dark
- [ ] Contrast ratio >= 4.5:1 para text
- [ ] ARIA labels em elementos interativos
- [ ] Responsive: testar em mobile (375px), tablet (768px), desktop (1920px)
- [ ] Sem cor como único indicador (use icons + color)
- [ ] Legends claras, tooltips com info completa
- [ ] Loading states (spinner, skeleton)
- [ ] Error states (mensagens legíveis)
```

### Simplify Checklist (`/simplify`)
```markdown
- [ ] Sem repetição > 2x (candidate para função)
- [ ] Sem abstrações prematuras (single-use class?)
- [ ] Pandas: operations chainable (não var intermediária)
- [ ] JSON schema: não redundância (latest + history não deveriam ter mesmos campos)
- [ ] Python: list comprehension em vez de loops
```

---

## PARTE 5: FERRAMENTAS ADICIONAIS RECOMENDADAS (não skills)

### Testing Framework
**Pytest** (já em plano)
- Unit tests: `test_heuristic.py` (mocks de SOQL data)
- Integration tests: `test_collect_and_predict.py` (fixture Salesforce?)
- Cobertura: >80% esperado

### Linting & Formatting
**Black** + **Flake8** (add `requirements.txt` dev)
```bash
black monitoring/scripts/*.py
flake8 monitoring/scripts/ --max-line-length=100
```
**Integração:** Pre-commit hook ou GitHub Actions (monitoring-tests.yml)

### Frontend Quality
**Lighthouse** (CLI)
```bash
npm install -g lighthouse
lighthouse site/index.html --chrome-flags="--headless"
```
**Targets:**
- Performance: > 90
- Accessibility: > 95 (crítico!)
- Best Practices: > 90
- SEO: > 85 (nice-to-have)

### Git Workflow
**Branch protection** em `master`:
- Require 1 approval (PR review)
- Require status checks (pytest, lighthouse)
- Dismiss stale PR approvals on new commits
- Require branches up to date before merging

### Monitoring (Fase 5)
**UptimeRobot** (free)
- Monitor que workflow rodou nos últimos 10 min
- Alert se health check falha
- Backup simples para observabilidade (complementa health banner no site)

---

## PARTE 6: EQUIPAMENTOS & AMBIENTE

### Hardware Recomendado (equipe)
- **Backend:** Linux VM ou macOS (Python dev)
- **Frontend:** IDE com DevTools (Chrome/Firefox)
- **DevOps:** GitHub (web), Terminal (git)
- **Ninguém precisa de:** GPU, Colab, servidor próprio

### Software Obrigatório
```bash
# Backend
python 3.11
pip
pytest
black
flake8

# Frontend
node 18+ (npm para dev tools opcionais)
chrome/firefox devtools

# DevOps
git
gh cli (GitHub)
```

### GitHub Secrets Pré-Requisito
```
SF_CLIENT_ID           = xxxxxxx
SF_CLIENT_SECRET       = xxxxxxx
SF_REFRESH_TOKEN       = xxxxxxx
SLACK_WEBHOOK_URL      = https://hooks.slack.com/... (Fase 2+)
SMTP_PASSWORD          = xxxxxxx (Fase 2+, email)
```

---

## SUMÁRIO: SKILLS CRÍTICAS POR ORDEM

### Tier 1 (OBRIGATÓRIO, cada semana)
1. `/code-review` — Validação de PR (backend)
2. `/dataviz` — Dashboard design (frontend)

### Tier 2 (IMPORTANTE, 1x por fase)
3. `/simplify` — Refactoring (backend)
4. `/loop` — Monitoring early phases (devops)

### Tier 3 (OPCIONAL, nice-to-have)
5. `/claude-api` — Se usar LLM em Fase 5+
6. `artifact-design` — Se criar mockups

### Não Aplicáveis
- `/derivatives-specialist-skill` (trading, não relevante)
- `/morning` (não é projeto de tarefas recorrentes)
- `web-artifacts-builder` (frontend é repo, não artifact)

---

**Pronto para iniciar implementação com confiança.**  
**Skills selecionadas garantem qualidade profissional em cada camada.**
