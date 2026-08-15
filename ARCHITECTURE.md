# ARQUITETURA: Monitoramento Preditivo + Dashboard de Casos
## Micro-serviços | Micro front-end | Testes | Logging Estruturado

**Data:** 2026-08-15  
**Status:** Plano de Arquitetura v1  
**Repositório:** brunotrolo/brunotrolo

---

## PRINCÍPIOS

1. **Isolamento por Domínio**: cada serviço tem responsabilidade única, pode ser testado isoladamente
2. **Contrato entre Serviços**: JSON schemas, não código compartilhado
3. **Sem Dependências Cíclicas**: A → B → C, nunca voltar para A
4. **Testes Primeiro**: mocks antes de dados reais, unit antes de integration
5. **Logging Imutável**: registrar cada evento exatamente como aconteceu, nunca apagar/editar

---

## ESTRUTURA DE DIRETÓRIOS

```
brunotrolo/
├── ARCHITECTURE.md                    (este arquivo)
├── PREDICTIVE_MONITORING_PLAN.md      (plano atualizado com Fase 0 mocks + testes)
├── CASE_EXECUTIVE_DASHBOARD_PLAN.md   (plano atualizado com Fase 0 mocks + testes)
│
├── services/                          (micro-serviços Python)
│   ├── collector/                     (busca dados Salesforce | Mock Salesforce)
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── collector.py           (orquestrador)
│   │   │   ├── salesforce_client.py   (REST API)
│   │   │   ├── mock_salesforce.py     (Fase 0: simula Salesforce)
│   │   │   └── schemas.py             (validação JSON: input/output)
│   │   ├── tests/
│   │   │   ├── test_collector.py      (unit: orquestração)
│   │   │   ├── test_salesforce_client.py (unit: REST chamadas)
│   │   │   ├── test_mock_salesforce.py (unit: dados mockados)
│   │   │   ├── conftest.py            (fixtures compartilhadas)
│   │   │   └── fixtures/              (dados mockados)
│   │   ├── requirements.txt           (pandas, requests, pydantic)
│   │   └── pytest.ini
│   │
│   ├── heuristic/                     (calcula risk_score)
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── heuristic.py           (EWMA, z-score, MAD)
│   │   │   └── schemas.py
│   │   ├── tests/
│   │   │   ├── test_heuristic.py
│   │   │   ├── conftest.py
│   │   │   └── fixtures/
│   │   ├── requirements.txt
│   │   └── pytest.ini
│   │
│   ├── aggregation/                   (calcula métricas de Cases)
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── aggregator.py
│   │   │   └── schemas.py
│   │   ├── tests/
│   │   │   ├── test_aggregator.py
│   │   │   ├── conftest.py
│   │   │   └── fixtures/
│   │   ├── requirements.txt
│   │   └── pytest.ini
│   │
│   ├── comparison/                    (heurística vs shadow ML)
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── compare_models.py      (precisão, recall, F1)
│   │   │   └── schemas.py
│   │   ├── tests/
│   │   │   ├── test_comparison.py
│   │   │   ├── conftest.py
│   │   │   └── fixtures/
│   │   ├── requirements.txt
│   │   └── pytest.ini
│   │
│   └── shared/                        (código agnóstico, reutilizável)
│       ├── logger.py                  (logging estruturado em JSON)
│       ├── schemas.py                 (JSON schemas base)
│       ├── errors.py                  (exceções padrão)
│       ├── utils.py                   (helpers: time buckets, retries, etc)
│       └── tests/
│           ├── test_logger.py
│           ├── test_schemas.py
│           ├── test_utils.py
│           └── conftest.py
│
├── site/                              (micro front-end)
│   ├── index.html                     (shell: carrega micro frontends)
│   ├── styles/
│   │   └── global.css                 (design system compartilhado)
│   ├── monitoring/                    (componente: dashboard monitoramento)
│   │   ├── app.js                     (orquestrador)
│   │   ├── dashboard.js               (renderiza risk score + histórico)
│   │   ├── alerts-panel.js            (panel de alertas)
│   │   ├── feedback-button.js         (botão falso positivo)
│   │   ├── mock-data.js               (Fase 0: simula API)
│   │   └── tests/
│   │       ├── test-dashboard.js      (Jest)
│   │       ├── test-alerts-panel.js
│   │       └── test-mock-data.js
│   ├── cases/                         (componente: dashboard casos)
│   │   ├── app.js
│   │   ├── case-dashboard.js          (renderiza toggles + métricas)
│   │   ├── toggles.js                 (agrupamento, período, escopo)
│   │   ├── charts.js                  (Google Charts integração)
│   │   ├── mock-data.js               (Fase 0: simula API)
│   │   └── tests/
│   │       ├── test-dashboard.js
│   │       ├── test-toggles.js
│   │       └── test-mock-data.js
│   └── shared/
│       ├── components.js              (Button, Card, Table, Chart — agnósticos)
│       ├── api-client.js              (fetch wrapper com retry, cache)
│       ├── test-utils.js              (helpers Jest: render, wait-for, etc)
│       └── tests/
│           ├── test-components.js
│           └── test-api-client.js
│
├── .github/workflows/
│   ├── monitoring-collect.yml         (cron: roda collector → heuristic → comparison)
│   ├── case-dashboard-collect.yml     (cron: roda collector → aggregation)
│   ├── monitoring-tests.yml           (pytest em services/collector, heuristic, comparison)
│   ├── case-dashboard-tests.yml       (pytest em services/aggregation)
│   ├── frontend-tests.yml             (Jest em site/)
│   └── monitoring-feedback.yml        (processa Issues)
│
└── docs/
    ├── LOGGING_GUIDE.md               (como logar eventos)
    ├── TESTING_GUIDE.md               (como escrever testes)
    ├── SERVICES_CONTRACTS.md          (input/output de cada serviço)
    └── DEBUGGING.md                   (como debugar com logs estruturados)
```

---

## LOGGING ESTRUTURADO

**Formato:** JSON Lines (cada evento é uma linha JSON)  
**Arquivo:** `/tmp/monitoring.log` (localizado via env var `LOG_FILE`)  
**Leitura:** Pode ser visualizado em GitHub Actions workflow logs ou com `tail -f`

**Evento padrão:**
```json
{
  "timestamp": "2026-08-15T14:05:30.123Z",
  "level": "INFO|DEBUG|WARN|ERROR",
  "service": "collector-service",
  "operation": "fetch_nebula_logs",
  "request_id": "req_abc123",
  "input": {
    "minutes": 30,
    "limit": 500
  },
  "output": {
    "count": 143,
    "duration_ms": 245
  },
  "error": null,
  "context": {
    "batch_id": "batch_001",
    "sf_org": "production"
  }
}
```

**Eventos críticos a registrar:**
- Início/fim de cada operação (com duração)
- Input recebido (validado/rejeitado)
- Output gerado (count, estrutura)
- Erro ocorrido (mensagem, stack trace, contexto)
- Cache hits/misses
- Rate limit warnings
- Retry attempts

**Exemplo de fluxo completo:**
```json
{"timestamp":"...", "level":"INFO", "service":"collector", "operation":"START_COLLECT", "input":{...}}
{"timestamp":"...", "level":"DEBUG", "service":"collector", "operation":"SALESFORCE_CONNECT", "output":{"session_id":"..."}}
{"timestamp":"...", "level":"DEBUG", "service":"collector", "operation":"FETCH_LOGS", "output":{"count":143}}
{"timestamp":"...", "level":"INFO", "service":"heuristic", "operation":"START_HEURISTIC", "input":{"log_count":143}}
{"timestamp":"...", "level":"DEBUG", "service":"heuristic", "operation":"BUCKET_AGGREGATION", "output":{"buckets_updated":12}}
{"timestamp":"...", "level":"DEBUG", "service":"heuristic", "operation":"RISK_CALCULATION", "output":{"risk_score":0.72}}
{"timestamp":"...", "level":"INFO", "service":"heuristic", "operation":"END_HEURISTIC", "output":{"risk_score":0.72, "duration_ms":520}}
```

**Leitura de logs:**
```bash
# Últimos 50 eventos
tail -50 /tmp/monitoring.log | jq .

# Filtrar por serviço
cat /tmp/monitoring.log | jq 'select(.service == "collector-service")'

# Filtrar por erro
cat /tmp/monitoring.log | jq 'select(.level == "ERROR")'

# Timeline de um request
cat /tmp/monitoring.log | jq 'select(.request_id == "req_abc123")' | jq -s 'sort_by(.timestamp)'
```

---

## TESTES UNITÁRIOS

**Pilar 1: Dados Mockados**
- `services/*/tests/fixtures/`: YAML/JSON com dados mockados
- `services/*/tests/conftest.py`: pytest fixtures que carregam mocks
- Fase 0: testes usam mocks
- Fase 1+: testes usam mocks de Salesforce real, mas não da API ao vivo

**Pilar 2: Testes Isolados**
- Cada serviço testado isoladamente (nenhuma chamada a outro serviço)
- Contrato validado via JSON schema, não via chamadas reais
- Exemplo: `test_heuristic.py` passa JSON válido, valida output com schema

**Pilar 3: Coverage Mínimo**
- Cada serviço: ≥80% coverage de linhas
- Cada componente front-end: ≥70% coverage
- CI bloqueia merge se coverage cair

**Fase 0 — Testes com Mocks:**
```bash
# Testar collector com mock Salesforce
pytest services/collector/tests/test_collector.py -v

# Testar heuristic com dados mockados
pytest services/heuristic/tests/test_heuristic.py -v

# Testar todo o pipeline com mocks (integration test)
pytest services/ -k "integration" -v
```

**Fase 1+ — Testes com Salesforce Real (opt-in):**
```bash
# Rodar testes contra Salesforce real (requer credenciais)
pytest services/collector/tests/test_collector.py -v --salesforce-real
```

---

## MICRO-SERVIÇOS: CONTRATOS

### Collector Service
**Input (via função Python):**
```json
{
  "minutes": 30,
  "limit": 500
}
```

**Output:**
```json
{
  "timestamp": "2026-08-15T14:05:30Z",
  "records": [
    {
      "id": "Log__c_001",
      "message": "POST /services/apexrest/cases",
      "service_duration_ms": 245,
      "status_code": 200,
      "created_date": "2026-08-15T14:05:00Z"
    }
  ],
  "count": 143,
  "source": "mock|salesforce"
}
```

### Heuristic Service
**Input:**
```json
{
  "records": [
    {
      "service_duration_ms": 245,
      "status_code": 200,
      "created_date": "2026-08-15T14:05:00Z"
    }
  ]
}
```

**Output:**
```json
{
  "timestamp": "2026-08-15T14:05:30Z",
  "risk_score": 0.72,
  "risk_level": "MEDIA",
  "alerts": [
    {
      "type": "latency_anomaly",
      "z_score": 2.3,
      "bucket": "wed_14h-14h05"
    }
  ]
}
```

### Comparison Service (Fase 3+)
**Input:**
```json
{
  "heuristic_score": 0.72,
  "shadow_ml_score": 0.81,
  "actual_incident": false
}
```

**Output:**
```json
{
  "heuristic_precision_7d": 0.78,
  "heuristic_recall_7d": 0.82,
  "shadow_ml_precision_7d": 0.81,
  "shadow_ml_recall_7d": 0.75,
  "recommendation": "heuristic_performing_better"
}
```

---

## MICRO FRONT-END

**Shell (`index.html`):**
- Carrega estilos globais (design system)
- Carrega ambos os micro frontends (`monitoring/app.js` e `cases/app.js`)
- Ambos convivem na mesma página, em abas ou side-by-side

**Micro Frontend 1: Monitoring Dashboard**
- Responsável: risk score, alertas, histórico, botão feedback
- Imports: `shared/components.js`, `shared/api-client.js`, `mock-data.js` (Fase 0)
- Testes: `monitoring/tests/test-dashboard.js` (Jest)

**Micro Frontend 2: Cases Dashboard**
- Responsável: toggles, métricas, gráficos, tabelas
- Imports: `shared/components.js`, `shared/api-client.js`, `charts.js`, `mock-data.js` (Fase 0)
- Testes: `cases/tests/test-dashboard.js` (Jest)

**Componentes Compartilhados (`shared/components.js`):**
```javascript
// Agnóstico, usado por ambos os dashboards
export function Button({label, onClick, disabled}) { ... }
export function Card({title, children}) { ... }
export function Table({columns, rows, onRowClick}) { ... }
export function Alert({type, message, onDismiss}) { ... }
export function Spinner({size}) { ... }
```

**API Client Compartilhado (`shared/api-client.js`):**
```javascript
// Wrapper de fetch com retry, cache, timeout
export async function fetchJSON(url, {cache: true, retries: 3, timeout: 10000}) { ... }
```

---

## FASE 0: DADOS MOCKADOS

**Objetivo:** Validar toda a arquitetura de micro-serviços + testes + logging **sem dependência de Salesforce**

**Setup:**
```bash
# Instalar dependências
pip install -r services/collector/requirements.txt
pip install -r services/heuristic/requirements.txt
# ... etc para cada serviço

npm install  # para front-end
```

**Rodar testes (todos com mocks):**
```bash
# Backend
pytest services/ -v --cov=services

# Frontend
npm test
```

**Rodar pipeline completo (com mocks):**
```bash
# Simula workflow de coleta + heurística + comparison
python monitoring/scripts/orchestrate.py --mode mock --log-file /tmp/monitoring.log
```

**Resultado:**
- Todos os JSONs são gerados (latest.json, history.json, predictions.json)
- Todos os logs são registrados
- Front-end consegue buscar dados de mock (antes de Pages real)
- 100% de cobertura de testes, zero dependência de Salesforce

**Transição para Fase 1:**
- Trocar `mock_salesforce.py` por `salesforce_client.py` (apenas 1 linha em `collector.py`)
- Adicionar credenciais OAuth nos GitHub Secrets
- Rodar novamente — tudo funciona igual, só muda a source dos dados

---

## FASE 1+: DADOS REAIS

**Sem mudanças na arquitetura**, apenas:
1. Remover flag `--mode mock`
2. Salesforce Client vai fazer chamadas reais
3. Logger continua registrando tudo igual

---

## DECISÕES TÉCNICAS

1. **Micro-serviços em Python** (não Go, não Rust): reutiliza `requests`, `pandas`, `prophet`, `scikit-learn`
2. **Testes com pytest + fixtures**: simples, poderoso, industria-padrão
3. **Logging em JSON Lines**: fácil de parsear, buscar, correlacionar eventos
4. **Mock-first**: Fase 0 toda com dados fake, valida lógica antes de depender de Salesforce
5. **Micro front-end sem framework pesado**: vanilla JS, sem webpack/build step na Fase 0 (apenas copia pra Pages)
6. **Contratos via JSON schemas** (pydantic Python-side, JSON schema JS-side): valida input/output de cada serviço

---

## SUCCESS CRITERIA

- ✅ Fase 0 conclui com todos os testes passando (pytest + Jest)
- ✅ Logs estruturados registram cada operação sem gaps
- ✅ Micro-serviços são testáveis isoladamente (mocks, fixtures)
- ✅ Micro front-end é testável isoladamente (Jest, componentes agnósticos)
- ✅ Não há dependências cíclicas (A → B → C, nunca ciclos)
- ✅ Coverage ≥80% backend, ≥70% frontend
- ✅ Transição para dados reais é trivial (1-2 linhas de código)
