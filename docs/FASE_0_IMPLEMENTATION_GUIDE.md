# FASE 0: IMPLEMENTATION GUIDE
**Projeto:** Salesforce Predictive Monitoring  
**Data:** 2026-08-15  
**Status:** Ready for Kickoff  
**Duração Estimada:** 3-4 dias

---

## 📋 OVERVIEW

Fase 0 é o scaffold do projeto com dados mockados. Nenhuma conexão Salesforce aqui - tudo funciona offline com dados fake para validar arquitetura, testes e pipeline.

### Objetivo Principal
Ter **100% funcional, 0% Salesforce** pronto para transição simples em Fase 1.

---

## 🎯 CHECKLIST: DEFINIÇÃO DE PRONTO (Phase 0)

- [ ] MCP Salesforce testado fora de sessão interativa
- [ ] Repositório scaffold criado com estrutura correta
- [ ] Todos testes passam (pytest + Jest com mocks)
- [ ] Coverage ≥80% backend, ≥70% frontend
- [ ] Logging estruturado (JSON Lines) valida cada operação
- [ ] Pipeline completo roda: collector → heuristic → JSON
- [ ] Frontend consegue buscar dados mock via API
- [ ] Health check banner valida timestamp
- [ ] Documentação atualizada (TESTING_GUIDE.md, SERVICES_CONTRACTS.md)
- [ ] ✅ Fase 0 pronta para transição MCP (Fase 1)

---

## 🔨 STEP-BY-STEP IMPLEMENTATION

### STEP 0: Instalar GitHub Skills & Dependências (1-2 horas)
**Objetivo:** Setup de todas as ferramentas necessárias para Fase 0

**Ferramentas a instalar (11 principais):**

#### Backend Python
```bash
# Validação + Logging + Testing
pip install pydantic structlog pytest pytest-cov faker black ruff mypy

# Requirements.txt de cada serviço (usar versões abaixo)
pytest==7.4.0
pytest-cov==4.1.0
pydantic==2.0.0
structlog==23.1.0
faker==19.0.0
```

#### Frontend JavaScript
```bash
cd site
npm init -y
npm install --save-dev jest tailwindcss
# shadcn/ui: componentes copy-paste (não npm install)
npm install --save-dev @types/jest @babel/preset-react
```

#### Development Tools (Pre-commit + Linting)
```bash
pip install pre-commit black ruff mypy

# Criar .pre-commit-config.yaml (veja seção "Git Hooks Setup" abaixo)
pre-commit install
```

**Resultado Esperado:**
```bash
# Verificar todas instalações
python --version                 # Python 3.10+
pip list | grep pydantic        # pydantic 2.0.0
npm --version                    # Node 18+
pytest --version                 # pytest 7.4.0
jest --version                   # jest 29+
black --version                  # black 23.7.0+
ruff --version                   # ruff 0.0.278+
mypy --version                   # mypy 1.4.1+
```

**Git Hooks Setup:**
```bash
# .pre-commit-config.yaml
cat > .pre-commit-config.yaml <<'EOF'
repos:
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
        language_version: python3.10
  
  - repo: https://github.com/astral-sh/ruff
    rev: v0.0.278
    hooks:
      - id: ruff
        args: [--fix]
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.4.1
    hooks:
      - id: mypy
        args: [--ignore-missing-imports]
        additional_dependencies: [types-all]
EOF

pre-commit install
```

**GitHub Skills Reference:**
- Pydantic: https://github.com/pydantic/pydantic (validação)
- structlog: https://github.com/hynek/structlog (logging)
- pytest: https://github.com/pytest-dev/pytest (testes backend)
- faker: https://github.com/joke2k/faker (mock data)
- Jest: https://github.com/jestjs/jest (testes frontend)
- Tailwind: https://github.com/tailwindlabs/tailwindcss (styling)
- shadcn/ui: https://github.com/shadcn-ui/ui (componentes)
- Black: https://github.com/psf/black (formatter)
- Ruff: https://github.com/astral-sh/ruff (linter)
- mypy: https://github.com/python/mypy (type checker)
- pre-commit: https://github.com/pre-commit/pre-commit (git hooks)

**→ Documentação completa:** `docs/GITHUB_SKILLS_REFERENCES.md`

---

### STEP 1: MCP Salesforce Validation (1-2 horas)
**Objetivo:** Confirmar que MCP funciona fora de sessão interativa

**Comandos:**
```bash
# Instalar MCP Salesforce
pip install mcp-salesforce

# Testar fora de sessão interativa
python -c "from mcp_salesforce import SalesforceClient; client = SalesforceClient(); print(client.soql_query('SELECT Id FROM Log__c LIMIT 1'))"
```

**Resultado Esperado:**
```
[ID of first Log__c record]
```

**Se falhar:** Investigar erro de autenticação MCP
**Se passar:** ✅ Pronto para Fase 1, proceed com Fase 0

---

### STEP 2: Scaffold Repositório (2 horas)

#### 2.1: Criar estrutura de diretórios
```bash
# Backend services
mkdir -p services/{collector,heuristic,comparison,shared}/{src,tests,fixtures}

# Frontend
mkdir -p site/{monitoring,shared,styles}

# Config
mkdir -p .github/workflows
mkdir -p docs
```

#### 2.2: Python project initialization
```bash
# Para cada serviço
for service in collector heuristic comparison; do
  # Requirements
  cat > services/$service/requirements.txt <<'EOF'
pytest==7.4.0
pytest-cov==4.1.0
pydantic==2.0.0
requests==2.31.0
pandas==2.0.0
structlog==23.1.0
EOF

  # pytest config
  cat > services/$service/pytest.ini <<'EOF'
[pytest]
testpaths = tests
addopts = --cov=src --cov-report=term-missing
EOF

  # Python package
  touch services/$service/src/__init__.py
done

# Shared utilities
cat > services/shared/requirements.txt <<'EOF'
pydantic==2.0.0
structlog==23.1.0
EOF
touch services/shared/src/__init__.py
```

#### 2.3: Frontend initialization
```bash
# Node/npm
cd site
npm init -y
npm install --save-dev jest @jest/globals

# Jest config
cat > jest.config.js <<'EOF'
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
};
EOF

cat > jest.setup.js <<'EOF'
global.fetch = jest.fn();
EOF
```

---

### STEP 3: Primeira Batch de Testes (Dia 1)

#### 3.1: Backend test — Mock data fixture

**File:** `services/collector/tests/fixtures/mock_logs.yaml`
```yaml
logs:
  - log_id: "LOG-001"
    timestamp: "2026-08-15T10:00:00Z"
    org_id: "ORG-123"
    status_code: 200
    duration_ms: 150
    resource: "/api/accounts"
    
  - log_id: "LOG-002"
    timestamp: "2026-08-15T10:01:00Z"
    org_id: "ORG-123"
    status_code: 500
    duration_ms: 2000
    resource: "/api/users"
    
  - log_id: "LOG-003"
    timestamp: "2026-08-15T10:02:00Z"
    org_id: "ORG-123"
    status_code: 200
    duration_ms: 300
    resource: "/api/products"
```

**File:** `services/collector/tests/conftest.py`
```python
import pytest
import yaml

@pytest.fixture
def mock_logs():
    with open("tests/fixtures/mock_logs.yaml") as f:
        return yaml.safe_load(f)["logs"]

@pytest.fixture
def collector_service():
    from src.collector import LogCollector
    return LogCollector()
```

**File:** `services/collector/tests/test_collector.py`
```python
def test_collector_loads_mock_logs(collector_service, mock_logs):
    result = collector_service.load(mock_logs)
    assert len(result) == 3
    assert result[0]["log_id"] == "LOG-001"

def test_collector_validates_schema(collector_service, mock_logs):
    result = collector_service.validate(mock_logs)
    assert result["valid"] == True
    assert result["errors"] == []
```

**Run tests:**
```bash
cd services/collector
pip install -r requirements.txt
pytest -v
```

#### 3.2: Frontend test — Mock data
**File:** `site/monitoring/mock-data.js`
```javascript
export const mockMonitoringData = {
  risk_score: 0.42,
  alerts: [
    { id: "A1", severity: "CRITICAL", message: "High error rate", timestamp: "2026-08-15T10:05:00Z" },
    { id: "A2", severity: "WARNING", message: "Slow response", timestamp: "2026-08-15T10:03:00Z" },
  ],
  health_check: {
    status: "HEALTHY",
    last_updated: "2026-08-15T10:05:00Z",
  }
};
```

**File:** `site/monitoring/tests/test-dashboard.js`
```javascript
import { mockMonitoringData } from '../mock-data.js';

describe('Dashboard', () => {
  test('renders risk score', () => {
    const { risk_score } = mockMonitoringData;
    expect(risk_score).toBe(0.42);
  });

  test('displays alerts', () => {
    const { alerts } = mockMonitoringData;
    expect(alerts.length).toBe(2);
    expect(alerts[0].severity).toBe('CRITICAL');
  });

  test('shows health check status', () => {
    const { health_check } = mockMonitoringData;
    expect(health_check.status).toBe('HEALTHY');
  });
});
```

**Run tests:**
```bash
cd site
npm install
npm test
```

---

### STEP 4: Logging Structure (Dia 1)

**File:** `services/shared/src/logger.py`
```python
import structlog
import json
from datetime import datetime

def setup_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

def get_logger(name: str):
    return structlog.get_logger(name)
```

**File:** `services/shared/tests/test_logger.py`
```python
import json
import io
import logging
from src.logger import setup_logging, get_logger

def test_logging_json_format(capsys):
    setup_logging()
    logger = get_logger("test_service")
    
    logger.info("test_event", service="collector", status="ok", duration_ms=150)
    
    captured = capsys.readouterr()
    log_entry = json.loads(captured.out.strip())
    
    assert log_entry["event"] == "test_event"
    assert log_entry["service"] == "collector"
    assert log_entry["status"] == "ok"
```

---

### STEP 5: Full Pipeline Mock (Dia 2-3)

**File:** `monitoring/orchestrate.py`
```python
#!/usr/bin/env python
import sys
import json
from datetime import datetime
import argparse

# Mock data generator
def generate_mock_monitoring_cycle():
    """Simula um ciclo completo: collector → heuristic → JSON output"""
    
    # Collector: Load logs
    logs = [
        {"log_id": "L1", "status_code": 200, "duration_ms": 100, "timestamp": datetime.utcnow().isoformat()},
        {"log_id": "L2", "status_code": 500, "duration_ms": 1500, "timestamp": datetime.utcnow().isoformat()},
        {"log_id": "L3", "status_code": 200, "duration_ms": 200, "timestamp": datetime.utcnow().isoformat()},
    ]
    
    # Heuristic: Analyze
    errors = len([l for l in logs if l["status_code"] >= 500])
    slow = len([l for l in logs if l["duration_ms"] > 1000])
    risk_score = min((errors * 0.3 + slow * 0.2) / len(logs), 1.0)
    
    # Generate alerts
    alerts = []
    if errors > 0:
        alerts.append({"severity": "CRITICAL", "message": f"{errors} errors detected"})
    if slow > 0:
        alerts.append({"severity": "WARNING", "message": f"{slow} slow requests"})
    
    # Output JSON
    result = {
        "timestamp": datetime.utcnow().isoformat(),
        "risk_score": risk_score,
        "errors_count": errors,
        "slow_requests_count": slow,
        "alerts": alerts,
        "health_check": {
            "status": "HEALTHY" if risk_score < 0.7 else "WARNING",
            "last_updated": datetime.utcnow().isoformat()
        }
    }
    
    return result, logs

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="mock", help="mock or live")
    parser.add_argument("--log-file", default="/tmp/monitoring.log", help="log output file")
    args = parser.parse_args()
    
    if args.mode != "mock":
        print("ERROR: Only mock mode supported in Fase 0")
        sys.exit(1)
    
    # Run pipeline
    result, logs = generate_mock_monitoring_cycle()
    
    # Validate output
    assert "risk_score" in result
    assert "alerts" in result
    assert "health_check" in result
    assert 0 <= result["risk_score"] <= 1
    
    # Write to file
    with open(args.log_file, 'w') as f:
        f.write(json.dumps(result) + "\n")
    
    print(f"✅ Pipeline complete: {args.log_file}")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
```

**Run:**
```bash
python monitoring/orchestrate.py --mode mock --log-file /tmp/monitoring.log
cat /tmp/monitoring.log
```

**Expected output:**
```json
{
  "timestamp": "2026-08-15T10:05:30.123456Z",
  "risk_score": 0.35,
  "errors_count": 1,
  "slow_requests_count": 1,
  "alerts": [
    {"severity": "CRITICAL", "message": "1 errors detected"},
    {"severity": "WARNING", "message": "1 slow requests"}
  ],
  "health_check": {
    "status": "HEALTHY",
    "last_updated": "2026-08-15T10:05:30.123456Z"
  }
}
```

---

## 📊 ARQUIVOS DE DOCUMENTAÇÃO A CRIAR

### 1. `docs/TESTING_GUIDE.md`
```markdown
# Testing Guide - Fase 0

## Backend (Python + pytest)
- Usar fixtures em conftest.py
- Mock external services (Salesforce em Fase 1)
- Coverage mínimo: 80%
- Rodar: pytest services/<service>/ -v

## Frontend (JavaScript + Jest)
- Mock API client com jest.fn()
- Mock data em mock-data.js
- Coverage mínimo: 70%
- Rodar: npm test

## Fixtures
- Dados fake em YAML
- Reutilizar em múltiplos testes
- Versionado no git
```

### 2. `docs/SERVICES_CONTRACTS.md`
```markdown
# Service Input/Output Contracts (JSON Schema)

## Collector Service
**Input:** `List<SalesforceLog>`
**Output:** `LogDataFrame`

## Heuristic Service
**Input:** `LogDataFrame`
**Output:** `MonitoringAlert[]`

## Comparison Service
**Input:** `MonitoringAlert[], HistoricalData`
**Output:** `MLPrediction`
```

### 3. `docs/ARCHITECTURE_DECISION_RECORDS.md`
```markdown
# ADRs - Architecture Decision Records

## ADR-001: Mock-First Strategy for Phase 0
- Decision: Use mock data only in Phase 0
- Rationale: Validate architecture without Salesforce dependency
- Consequences: Zero-to-Salesforce transition in Phase 1 (1-2 lines change)

## ADR-002: JSON as Primary Data Format
- Decision: All inter-service communication via JSON
- Rationale: Language-agnostic, easy debugging
- Consequences: Slight performance overhead (acceptable for monitoring)
```

---

## 🚀 EXECUÇÃO REALISTA (Timeline)

| Dia | Tarefa | Duração | Owner |
|-----|--------|---------|-------|
| 1 AM | MCP Salesforce validation | 1-2h | DevOps/SRE |
| 1 PM | Repository scaffold | 2h | Backend Eng |
| 1 PM | Backend fixtures + tests | 2h | Backend Eng |
| 2 AM | Frontend tests + mock data | 2h | Frontend Eng |
| 2 PM | Logging structure + tests | 1.5h | Backend Eng |
| 3 AM | Full pipeline orchestration | 2h | Backend Eng |
| 3 PM | Documentation + validation | 1h | Tech Lead |
| **TOTAL** | | **11.5h** | **3 people × 2 days** |

---

## ✅ VALIDAÇÃO FINAL

Run this checklist before marking Phase 0 DONE:

```bash
# Backend
pytest services/collector -v
pytest services/heuristic -v
pytest services/comparison -v
pytest services/shared -v

# Coverage check
pytest services/ --cov=src --cov-report=term-missing | grep -E "TOTAL|^services"

# Frontend
cd site && npm test

# Pipeline
python monitoring/orchestrate.py --mode mock --log-file /tmp/test.log
cat /tmp/test.log | python -m json.tool
```

**All passing = ✅ Phase 0 Complete**

---

## 📌 IMPORTANT NOTES

1. **Zero Salesforce in Phase 0:** All data is mocked
2. **JSON everywhere:** Inter-service contracts are JSON
3. **Structured logging:** Every operation logs to JSON Lines
4. **High test coverage:** ≥80% backend, ≥70% frontend
5. **Documentation:** TESTING_GUIDE, SERVICES_CONTRACTS, ADRs in docs/

---

## 🔄 PHASE 0 → PHASE 1 TRANSITION

When Phase 0 is complete:

```python
# Phase 0 collector (mock)
logs = mock_logs

# Phase 1 collector (MCP Salesforce) - 2 line change!
from mcp_salesforce import SalesforceClient
client = SalesforceClient()
logs = client.query_logs(limit=100)  # Real data
```

That's it! Everything else stays the same.

---

**Status:** Ready for Kickoff  
**Next Step:** Start Step 1 (MCP Validation) immediately  
**Contact:** @brunotrolo for questions
