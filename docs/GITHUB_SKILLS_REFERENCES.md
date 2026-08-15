# GITHUB SKILLS & REFERÊNCIAS - SALESFORCE PREDICTIVE MONITORING
**Data:** 2026-08-15  
**Projeto:** Salesforce Predictive Monitoring  
**Status:** Integrado ao Plano Técnico

---

## 📌 VISÃO GERAL

Este documento lista todos os projetos GitHub que servem como referência ou são dependências diretas para o desenvolvimento do projeto. Cada skill tem justificativa, link e fase de integração.

---

## 🎨 FRONTEND (JavaScript/HTML/CSS)

### 1. shadcn/ui
**GitHub:** https://github.com/shadcn-ui/ui  
**Status:** ✅ USAR EM FASE 0  
**Instalação:** Copy-paste de componentes  

**O que oferece:**
- Componentes React prontos para usar
- Acessibilidade WCAG 2.1 AA built-in
- Design consistente
- Customizável com Tailwind

**Por que usar:**
- Dashboard monitoring precisa de: Card, Button, Badge, Alert
- Componentes testados e acessíveis
- Zero tempo de setup

**Para o projeto:**
```javascript
// site/shared/components/
├── Card.jsx          ← shadcn/ui (risk score card)
├── Alert.jsx         ← shadcn/ui (alerts panel)
├── Badge.jsx         ← shadcn/ui (severity badges)
└── Button.jsx        ← shadcn/ui (action buttons)
```

**Fase:** 0 (imediatamente)  
**Esforço:** 1-2 horas (copy-paste + customização)

---

### 2. Tailwind CSS
**GitHub:** https://github.com/tailwindlabs/tailwindcss  
**Status:** ✅ USAR EM FASE 0  
**Instalação:** CDN ou npm  

**O que oferece:**
- Utility-first CSS framework
- Dark mode automático
- Responsivo mobile-first
- Temas customizáveis

**Por que usar:**
- Dashboard 24/7 precisa suportar dark mode
- Mobile responsiveness (acesso via celular)
- Componentes consistentes com shadcn/ui
- Sem build complexo

**Para o projeto:**
```html
<!-- site/monitoring/index.html -->
<link href="https://cdn.tailwindcss.com" rel="stylesheet">

<!-- Dark mode + responsive -->
<div class="dark:bg-gray-900 bg-white p-4 sm:p-8">
  <h1 class="text-2xl sm:text-3xl dark:text-white font-bold">
    Monitoring Dashboard
  </h1>
</div>
```

**Fase:** 0 (imediatamente)  
**Esforço:** Já incluído no projeto (zero extra)

---

### 3. Storybook
**GitHub:** https://github.com/storybookjs/storybook  
**Status:** ⚠️ OPCIONAL (Fase 1+)  
**Instalação:** npm install  

**O que oferece:**
- Desenvolvimento isolado de componentes
- Documentação automática
- Testes visuais
- Preview de estados

**Por que usar:**
- Testar componentes isoladamente
- Documentação automática para equipe
- Feedback loop rápido

**Para o projeto:**
```bash
# Fase 1+ (opcional)
npm install -D @storybook/react

# site/monitoring/stories/
├── Card.stories.jsx
├── Alert.stories.jsx
└── Badge.stories.jsx
```

**Fase:** 1+ (opcional)  
**Esforço:** 4-6 horas setup + histórias

---

## 🔧 BACKEND (Python)

### 4. Pydantic
**GitHub:** https://github.com/pydantic/pydantic  
**Status:** ✅ USAR EM FASE 0  
**Instalação:** `pip install pydantic`  

**O que oferece:**
- Validação de dados com type hints
- Serialização/desserialização JSON automática
- Schema validation
- Error messages claras

**Por que usar:**
- Validar entrada/saída de cada serviço
- JSON serialization automática
- Type safety em Python

**Para o projeto:**
```python
# services/*/src/schemas.py
from pydantic import BaseModel

class Log(BaseModel):
    log_id: str
    status_code: int
    duration_ms: int
    timestamp: str

class Alert(BaseModel):
    severity: str  # CRITICAL, WARNING, INFO
    message: str
    timestamp: str
```

**Fase:** 0 (imediatamente)  
**Esforço:** Já incluído nas estimativas

---

### 5. structlog
**GitHub:** https://github.com/hynek/structlog  
**Status:** ✅ USAR EM FASE 0  
**Instalação:** `pip install structlog`  

**O que oferece:**
- Logging estruturado em JSON Lines
- Context preservação automática
- Correlação de requests
- Processadores customizáveis

**Por que usar:**
- Logs queryáveis (grep, jq, etc)
- Métricas extraíveis
- Debugging facilitado

**Para o projeto:**
```python
# services/shared/src/logger.py
import structlog

logger = structlog.get_logger()
logger.info("collector_start", service="collector", count=523)
# Output: {"timestamp": "...", "level": "info", "event": "collector_start", ...}
```

**Fase:** 0 (imediatamente)  
**Esforço:** Já incluído nas estimativas

---

### 6. pandas
**GitHub:** https://github.com/pandas-dev/pandas  
**Status:** ✅ USAR EM FASE 1  
**Instalação:** `pip install pandas`  

**O que oferece:**
- DataFrames para análise de dados
- Agregações e cálculos eficientes
- Manipulação de séries temporais
- Exportação em múltiplos formatos

**Por que usar:**
- Análise de logs (risk score calculation)
- Agregações por período
- Performance em datasets grandes

**Para o projeto:**
```python
# services/heuristic/src/heuristic.py
import pandas as pd

logs_df = pd.DataFrame(logs)
errors = logs_df[logs_df['status_code'] >= 500]
slow = logs_df[logs_df['duration_ms'] > 1000]
risk_score = (len(errors) * 0.3 + len(slow) * 0.2) / len(logs_df)
```

**Fase:** 1 (coleta real de dados)  
**Esforço:** 2-3 horas implementação

---

### 7. FastAPI
**GitHub:** https://github.com/tiangolo/fastapi  
**Status:** ⚠️ OPCIONAL (Fase 2+)  
**Instalação:** `pip install fastapi`  

**O que oferece:**
- Framework web moderno
- OpenAPI (Swagger) automático
- Validação Pydantic built-in
- Async/await nativo

**Por que usar:**
- Se precisar API REST para dashboard
- Documentação automática
- Validação automática

**Para o projeto:**
```python
# monitoring/api.py (Fase 2+ opcional)
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

@app.get("/api/risk-score")
async def get_risk_score():
    return {"risk_score": 0.42, "timestamp": "..."}
```

**Fase:** 2+ (opcional)  
**Esforço:** 4-6 horas setup

---

## 🧪 TESTING (Python/JavaScript)

### 8. pytest
**GitHub:** https://github.com/pytest-dev/pytest  
**Status:** ✅ USAR EM FASE 0  
**Instalação:** `pip install pytest pytest-cov`  

**O que oferece:**
- Framework de testes mais usado em Python
- Fixtures poderosas (conftest.py)
- Plugins extensíveis
- Coverage reporting

**Por que usar:**
- Testes rápidos (unit tests)
- Mocks fáceis
- Coverage tracking

**Para o projeto:**
```bash
# services/*/tests/
pytest -v --cov=src --cov-report=term-missing

# Target: ≥80% coverage
```

**Fase:** 0 (imediatamente)  
**Esforço:** Já incluído nas estimativas

---

### 9. faker
**GitHub:** https://github.com/joke2k/faker  
**Status:** ✅ USAR EM FASE 0  
**Instalação:** `pip install faker`  

**O que oferece:**
- Gerador de dados fake realistas
- Suporte a múltiplos idiomas
- Fixtures consistentes
- Seeding para reprodução

**Por que usar:**
- Gerar mock_logs.yaml
- Dados realistas para testes
- Diversidade de casos

**Para o projeto:**
```python
# services/collector/tests/conftest.py
from faker import Faker

fake = Faker()

@pytest.fixture
def mock_logs():
    return [
        {
            "log_id": fake.uuid4(),
            "timestamp": fake.iso8601(),
            "status_code": fake.random_int(200, 599),
            "duration_ms": fake.random_int(50, 5000)
        }
        for _ in range(100)
    ]
```

**Fase:** 0 (imediatamente)  
**Esforço:** 1-2 horas

---

### 10. factory_boy
**GitHub:** https://github.com/FactoryBoy/factory_boy  
**Status:** ⚠️ OPCIONAL (Fase 1+)  
**Instalação:** `pip install factory-boy`  

**O que oferece:**
- Test fixtures builders
- Relações entre objetos
- Customização fácil
- Padrão DRY para testes

**Por que usar:**
- Fixtures mais semânticas
- Reutilização entre testes
- Menos duplicação

**Para o projeto:**
```python
# services/collector/tests/factories.py (Fase 1+ opcional)
import factory

class LogFactory(factory.Factory):
    class Meta:
        model = Log
    
    log_id = factory.Faker('uuid4')
    timestamp = factory.Faker('iso8601')
    status_code = factory.Faker('random_int', min=200, max=599)
```

**Fase:** 1+ (opcional)  
**Esforço:** 2-3 horas

---

### 11. Jest
**GitHub:** https://github.com/jestjs/jest  
**Status:** ✅ USAR EM FASE 0  
**Instalação:** `npm install --save-dev jest`  

**O que oferece:**
- Framework de testes JavaScript
- Snapshots testing
- Coverage built-in
- Mock automático de módulos

**Por que usar:**
- Testes frontend isolados
- Coverage tracking
- Rápido e confiável

**Para o projeto:**
```bash
# site/
npm test
npm test -- --coverage

# Target: ≥70% coverage
```

**Fase:** 0 (imediatamente)  
**Esforço:** Já incluído nas estimativas

---

## ⚙️ DEVOPS & QUALIDADE

### 12. pre-commit
**GitHub:** https://github.com/pre-commit/pre-commit  
**Status:** ⚠️ RECOMENDADO (Fase 0)  
**Instalação:** `pip install pre-commit`  

**O que oferece:**
- Git hooks framework
- Rodar verificações antes de commit
- Enforce padrões na equipe
- Configuração centralizada

**Por que usar:**
- Prevenir commits com código ruim
- Enforce padrões de qualidade
- Economia de tempo em review

**Para o projeto:**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
  
  - repo: https://github.com/astral-sh/ruff
    rev: v0.0.278
    hooks:
      - id: ruff
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.4.1
    hooks:
      - id: mypy
```

**Fase:** 0 (setup, enforce na equipe)  
**Esforço:** 1-2 horas setup

---

### 13. Ruff
**GitHub:** https://github.com/astral-sh/ruff  
**Status:** ✅ USAR EM FASE 0  
**Instalação:** `pip install ruff`  

**O que oferece:**
- Linter Python ultra-rápido (100x Flake8)
- Substitui Flake8 + isort + pyupgrade
- Zero configuração
- Detecção de bugs comum

**Por que usar:**
- Detectar bugs antes de runtime
- Padrão PEP 8
- Muito rápido em pre-commit

**Para o projeto:**
```bash
# CI/CD
ruff check services/

# Resultados
# services/collector/src/collector.py:10:1: F841 local variable 'x' is assigned to but never used
```

**Fase:** 0 (imediatamente)  
**Esforço:** Sem extra (apenas configuração)

---

### 14. Black
**GitHub:** https://github.com/psf/black  
**Status:** ✅ USAR EM FASE 0  
**Instalação:** `pip install black`  

**O que oferece:**
- Code formatter opinionado
- Zero configuração (determinístico)
- Padrão indústria
- Integração em pre-commit

**Por que usar:**
- Todos commits com mesmo padrão
- Sem debates sobre formatação
- Automático no pre-commit

**Para o projeto:**
```bash
# Pre-commit automático
black services/

# Antes:
def foo(x,y,z):return x+y+z

# Depois:
def foo(x, y, z):
    return x + y + z
```

**Fase:** 0 (imediatamente)  
**Esforço:** Sem extra

---

### 15. mypy
**GitHub:** https://github.com/python/mypy  
**Status:** ✅ USAR EM FASE 0  
**Instalação:** `pip install mypy`  

**O que oferece:**
- Type checker estático
- Validação de type hints
- Prevenção de bugs de tipo
- Integração IDE

**Por que usar:**
- Catch type errors cedo
- Melhor IDE autocomplete
- Documentação automática

**Para o projeto:**
```bash
# CI/CD
mypy services/ --ignore-missing-imports

# Detecta
# services/heuristic/src/heuristic.py:15: error: Argument 1 to "analyze" has incompatible type "str"; expected "List[Dict[str, Any]]"
```

**Fase:** 0 (imediatamente)  
**Esforço:** Sem extra

---

## 📊 LOGGING & MONITORING (Fase 5+)

### 16. Sentry
**GitHub:** https://github.com/getsentry/sentry  
**Status:** ⚠️ FASE 5+ (Hardening)  
**Instalação:** `pip install sentry-sdk`  

**O que oferece:**
- Error tracking em produção
- Aggregação de erros
- Stack traces detalhados
- Alertas automáticos

**Por que usar:**
- Fase 5 (hardening): rastrear erros em produção
- Responder rápido a problemas
- Análise de trends de erros

**Para o projeto:**
```python
# Fase 5+ apenas
import sentry_sdk

sentry_sdk.init(
    dsn="https://xxx@xxx.ingest.sentry.io/xxx",
    traces_sample_rate=1.0
)

# Erros automaticamente capturados
```

**Fase:** 5+ (hardening)  
**Esforço:** 2-3 horas setup

---

### 17. Prometheus
**GitHub:** https://github.com/prometheus/prometheus  
**Status:** ⚠️ FASE 5+ (Métricas)  
**Instalação:** Docker ou binary  

**O que oferece:**
- Time-series database
- Coleta de métricas
- Alertas baseados em métricas
- Visualização com Grafana

**Por que usar:**
- Fase 5: monitorar performance
- Alertas automáticos
- Histórico de métricas

**Para o projeto:**
```python
# Fase 5+ apenas
from prometheus_client import Counter, Histogram

collector_errors = Counter('collector_errors_total', 'Total errors')
heuristic_duration = Histogram('heuristic_duration_seconds', 'Analysis duration')
```

**Fase:** 5+ (monitoramento)  
**Esforço:** 4-6 horas setup

---

## 📋 MATRIZ DE INTEGRAÇÃO POR FASE

### FASE 0 (Scaffold + Mock) - INSTALE AGORA

| Skill | Tipo | Instalação | Esforço | Crítico? |
|-------|------|-----------|---------|----------|
| Pydantic | Backend | pip | ✅ Incluído | SIM |
| structlog | Backend | pip | ✅ Incluído | SIM |
| pytest | Testing | pip | ✅ Incluído | SIM |
| pytest-cov | Testing | pip | ✅ Incluído | SIM |
| faker | Testing | pip | 1-2h | SIM |
| Jest | Testing | npm | ✅ Incluído | SIM |
| Tailwind CSS | Frontend | CDN/npm | ✅ Incluído | SIM |
| shadcn/ui | Frontend | Copy-paste | 1-2h | SIM |
| Ruff | DevOps | pip | Automatizado | Recomendado |
| Black | DevOps | pip | Automatizado | Recomendado |
| mypy | DevOps | pip | Automatizado | Recomendado |
| pre-commit | DevOps | pip | 1-2h | Recomendado |

**Total Fase 0:** ~6-8 horas extras (além do desenvolvimento)

---

### FASE 1 (MCP Salesforce) - ADICIONE

| Skill | Tipo | Instalação | Esforço | Crítico? |
|-------|------|-----------|---------|----------|
| pandas | Backend | pip | 2-3h | SIM |
| factory_boy | Testing | pip | 2-3h | Opcional |
| Storybook | Frontend | npm | 4-6h | Opcional |

**Total Fase 1:** ~4-6 horas extras

---

### FASE 5+ (Hardening) - ADICIONE

| Skill | Tipo | Instalação | Esforço | Crítico? |
|-------|------|-----------|---------|----------|
| Sentry | Monitoring | pip | 2-3h | Opcional |
| Prometheus | Monitoring | Docker | 4-6h | Opcional |

**Total Fase 5+:** ~6-9 horas extras

---

## 🚀 PLANO DE INTEGRAÇÃO DETALHADO

### DIA 1 (Phase 0) - 2 horas de setup

```bash
# Backend requirements
pip install pydantic structlog pytest pytest-cov faker black ruff mypy

# Frontend
npm install tailwindcss jest
# Copy componentes shadcn/ui via CLI

# Git hooks
pip install pre-commit
pre-commit install
```

### DIA 2-3 (Phase 0) - Usar durante desenvolvimento

```bash
# Cada commit
pre-commit run --all-files

# Cada feature
pytest services/ --cov=src --cov-report=term-missing
npm test -- --coverage

# Antes de push
git push  # pre-commit roda automaticamente
```

### FASE 1 - Adicionar pandas

```bash
pip install pandas

# Usar em services/heuristic/src/heuristic.py
# Análise de logs com DataFrames
```

### FASE 5+ - Adicionar monitoring

```bash
# Erro tracking
pip install sentry-sdk

# Métricas
docker run -p 9090:9090 prom/prometheus
pip install prometheus-client
```

---

## 📊 RESUMO: DEPENDÊNCIAS PRINCIPAIS

```
Salesforce_PredictiveMonitoring/
│
├── services/
│   ├── collector/
│   │   └── requirements.txt
│   │       ├── pydantic        ✅
│   │       ├── structlog       ✅
│   │       ├── pytest          ✅
│   │       ├── faker           ✅
│   │       └── pandas          (Fase 1)
│   │
│   ├── heuristic/
│   │   └── requirements.txt
│   │       ├── pydantic        ✅
│   │       ├── structlog       ✅
│   │       ├── pytest          ✅
│   │       ├── pandas          (Fase 1)
│   │       └── factory_boy     (Fase 1 opt)
│   │
│   └── shared/
│       └── requirements.txt
│           ├── pydantic        ✅
│           └── structlog       ✅
│
├── site/
│   ├── package.json
│   │   ├── jest                ✅
│   │   ├── tailwindcss         ✅
│   │   ├── shadcn/ui           ✅
│   │   └── @storybook/react    (Fase 1 opt)
│   │
│   └── .pre-commit-config.yaml
│       ├── black               ✅
│       ├── ruff                ✅
│       └── mypy                ✅
│
└── .github/
    └── workflows/
        └── test.yml
            └── pytest + npm test (usa todas acima)
```

---

## ✅ CHECKLIST: GITHUB SKILLS INTEGRADAS

- [x] Pydantic (validação)
- [x] structlog (logging)
- [x] pytest (testes backend)
- [x] faker (mock data)
- [x] Jest (testes frontend)
- [x] Tailwind CSS (styling)
- [x] shadcn/ui (componentes)
- [x] Black (formatting)
- [x] Ruff (linting)
- [x] mypy (type checking)
- [x] pre-commit (git hooks)
- [ ] pandas (Fase 1)
- [ ] factory_boy (Fase 1 opt)
- [ ] Storybook (Fase 1 opt)
- [ ] Sentry (Fase 5+)
- [ ] Prometheus (Fase 5+)

---

## 💡 RECOMENDAÇÃO FINAL

**INSTALE EM FASE 0:**
Todos os projetos marcados com ✅ (essencial)

**LEIA ANTES DE COMEÇAR:**
- Pydantic docs (10 min)
- pytest docs (15 min)
- Tailwind CSS utilities (10 min)

**NÃO PRECISA APRENDER AGORA:**
- pandas (Fase 1)
- Storybook (Fase 1 opt)
- Sentry, Prometheus (Fase 5+)

---

**Última atualização:** 2026-08-15  
**Status:** Integrado ao plano técnico  
**Próximo passo:** Executar Fase 0 com estas skills

Links diretos para documentação oficial em cada seção acima.
