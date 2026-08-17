# Spec: Hardening & Scale (Phase 5)

> Fase 5 do `PROJECT_ROADMAP_MASTER.md` — documenta o que será construído,
> por quê e como será validado. Fonte de verdade enquanto a fase não está
> implementada; depois de implementada, o `describe()`/contratos de teste de
> cada serviço assumem.

Status: **Implemented (17/08/2026)** — `services/resilience` (22 testes, 100%),
retry/rate-limit em `mcp_salesforce.py`, Sentry opt-in, `metrics.py` (100%),
hardening do pipeline com bloco `pipeline` e `step_errors`, card "Pipeline
(último ciclo)" no dashboard. 89 testes em `monitoring` (91% cobertura), 55
frontend, ruff limpo, CI verde. Wiring do `collect.yml` feito no mesmo dia:
`--metrics-file` (`.prom` na branch `data`), `SENTRY_DSN` (secret opt-in) e
`--feedback-file` (lido da branch `data`).

---

## Objective

Endurecer o pipeline de monitoramento para rodar em produção (cron de 15 min
no GitHub Actions) sem perder ciclos por falhas transitórias e com
observabilidade mínima:

1. **Error handling & retries** → retry com backoff exponencial + jitter nas
   chamadas de rede (MCP/HTTP), classificando erros transitórios vs
   permanentes.
2. **Rate limiting & backoff** → token bucket para limitar a frequência de
   chamadas ao MCP (soqlQuery) e respeitar quotas da API.
3. **Sentry error tracking** → captura de exceções não tratadas quando
   `SENTRY_DSN` está presente; no-op sem DSN (nenhuma dependência em runtime
   sem config).
4. **Prometheus metrics** → snapshot exposto também no formato de text
   exposition do Prometheus (`metrics.prom`), para scraping futuro sem
   servidor: pipeline é batch, não serviço HTTP.
5. **Production monitoring** → metadados de execução no próprio snapshot
   (`pipeline`: duração, erros por passo) e exibição do status do último
   ciclo no dashboard.

Decisão de produto (mantida das Fases 3/4): tudo é **observacional** — retry
e rate limit mudam apenas transporte, nunca as regras de negócio do risco.

## Tech Stack & Commands

- Python 3.14 (padrão do CI), pytest, ruff, pip-audit — mesmas ferramentas das
  fases anteriores.
- `sentry-sdk` adicionado em `monitoring/requirements.txt` (o CI já instala
  esse arquivo e o pip-audit audita; sem DSN o SDK é no-op).

```bash
# Serviço novo (resiliência)
cd services/resilience
python -m pytest -q --cov=resilience --cov-report=term-missing
python -m ruff check resilience tests
python -m ruff format resilience tests

# Pipeline (monitoring)
cd monitoring
python -m pytest -q
python -m ruff check orchestrate.py mcp_salesforce.py metrics.py tests

# Frontend
cd site
npm test
node scripts/sync-dashboard.mjs --check
```

## Structure

```
services/resilience/          → pacote pip "resilience" (monitoring-resilience)
  pyproject.toml              → monitoring-resilience 0.1.0
  requirements.txt            → pytest, pytest-cov, faker, ruff (sem `-e .`)
  resilience/
    __init__.py               → exporta retry, TokenBucket, RetryExhausted,
                                is_retryable_error
    retry.py                  → retry com backoff exp + jitter; classifica erros
    rate_limit.py             → TokenBucket (rate + capacity)
  tests/
    conftest.py               → fixtures (sleeper fake, fn que falha N vezes)
    test_retry.py             → contratos e bordas (100% cobertura)
    test_rate_limit.py        → contratos e bordas (100% cobertura)

monitoring/
  mcp_salesforce.py           → retry em `_rpc` para erros transitórios;
                                token bucket opcional (env SF_MAX_QPS)
  metrics.py                  → build_prometheus_metrics(snapshot, duration)
                                → string text exposition (Prometheus)
  orchestrate.py              → bloco `pipeline` no snapshot (duration_ms,
                                steps, step_errors); init Sentry opcional
                                (env SENTRY_DSN); flag --metrics-file
  tests/
    test_orchestrate.py       → TestHardening (pipeline block, sentry no-op,
                                step errors isolados)
    test_metrics.py           → formato Prometheus (100% do módulo metrics)
    test_mcp_salesforce.py    → retry em transporte, classificação 429/5xx,
                                token bucket aplicado

site/monitoring/
  dashboard.js                → helper summarizePipeline (ok/falha, duração)
  mock-data.js                → pipeline nos mocks
  tests/test-dashboard.js     → testes do novo helper
docs/dashboard/               → header mostra status do último ciclo
  index.html
  assets/app.js
  assets/dashboard.js         (espelhado do site via sync-dashboard.mjs)
```

## Code Style

- Mesmas convenções das fases anteriores: Python 3.14, `from __future__ import
  annotations`, type hints completos, pydantic onde há contrato, funções
  puras testáveis (sleep injetável, relógio injetável), sem IO em funções de
  decisão.
- `var`/namespace único não se aplica (Python) — módulo único por conceito:
  `retry.py` e `rate_limit.py`.
- Frontend: helpers puros em `site/monitoring/dashboard.js` + testes Jest,
  espelhados para `docs/dashboard/assets/` via `sync-dashboard.mjs`.

## Testing Strategy

- **Unit (services/resilience):** pytest, 100% de cobertura exigida.
  - `retry`: sucesso na 1ª tentativa → 1 chamada; sucesso após N falhas
    transitórias → N+1 chamadas com backoff; `RetryExhausted` após
    esgotar; erro permanente (não-retryable) → re-raise imediato sem
    espera; jitter não-negativo; `retries=0` → 1 tentativa; sleep injetado
    (zero nos testes).
  - `TokenBucket`: arranca cheio; `acquire(1)` contínuo respeita rate;
    `acquire(n > capacity)` → False/levanta; recarga ao longo do tempo
    (relógio fake).
- **Pipeline (monitoring):** testes existentes seguem verdes; novos:
  - `metrics.py`: snapshot → texto com `# HELP`/`# TYPE`, valores
    numéricos, timestamp, sanitização de labels.
  - retry no client: 500 → retry e sucesso; 429 → retry; 400 → sem retry;
    timeout (URLError) → retry; token bucket chamado quando `SF_MAX_QPS`
    definido.
  - pipeline block: `duration_ms` >= 0, `steps` lista, erro de passo
    opcional não derruba o resultado (registrado em `step_errors`).
  - Sentry: sem `SENTRY_DSN` → `init_sentry` retorna sem efeito; com DSN
    fake → `sentry_sdk.init` chamado (mock).
- **Frontend (Jest):** `summarizePipeline` com/ sem `pipeline` block.
- **Definição de verde:** pytest completo do repo, ruff check/format, npm
  test, `sync-dashboard.mjs --check` — idem CI.

## Boundaries

- Retry **só** em transporte (HTTP 429/5xx, URLError/timeout); nunca retenta
  erros de protocolo MCP (MALFORMED_QUERY etc.), auth 401 (já tem refresh
  próprio) nem validação de dados.
- Token bucket aplicado **apenas** ao `soqlQuery`/`call_tool` quando
  `SF_MAX_QPS` está definido no ambiente; sem env var, comportamento atual
  (sem limite) — mudança não-observável em runtime.
- Sentry é **opcional**: sem `SENTRY_DSN` o pipeline roda exatamente como
  hoje; DSN vem só de variável de ambiente (nunca no código/repo).
- `metrics.prom` é um artefato derivado do snapshot — nenhum endpoint HTTP,
  nenhum servidor.
- Nenhum passo opcional (shadow, accuracy, feedback, comparison) derruba o
  pipeline: falha vira `step_errors` com o passo identificado. Coleta
  continua sendo o único passo fatal.
- Dashboard: apenas exibe; nenhuma regra de negócio no cliente.
- **Não** tocar `.github/workflows/` sem decisão explícita do usuário
  (wiring de `--metrics-file`/`SENTRY_DSN`/`--feedback-file` no `collect.yml`
  fica como open question — é mudança de workflow, não de código).

## Success Criteria

1. `services/resilience` com 100% de cobertura; suíte completa do repo verde
   (pytest services/* + monitoring, ruff, npm test, sync --check).
2. Pipeline mock com `SF_MAX_QPS=...`/retry exercitados em teste não-regressivo
   (client fake com falha transitória → retry e sucesso no 2º hit).
3. `python orchestrate.py --mode mock --metrics-file out/metrics.prom` →
   arquivo com formato text exposition válido (parseável, contém
   `monitoring_risk_score` e `monitoring_logs_processed`).
4. Snapshot mock contém `pipeline` com `duration_ms` e `steps`; dashboard
   mostra status do último ciclo.
5. `SPECIFICATION.md` §3.3 Phase 5 e `PROJECT_ROADMAP_MASTER.md` marcadas
   como implementadas; `docs/HARDENING_SPEC.md` com Status: Implemented.

## Open Questions

1. ~~**Wiring no `collect.yml`**~~ ✅ **Resolvido (17/08/2026):** o workflow
   agora passa `--metrics-file` (grava `${STAMP}.prom` na branch `data` junto
   do snapshot e no artifact), `SENTRY_DSN` (secret, opt-in — sem o secret o
   pipeline roda idêntico) e `--feedback-file` (baixa `feedback.json` da raiz
   da branch `data` quando existe).
2. **Thresholds de retry em produção:** `retries=3`, `base_delay=1s`,
   `max_delay=30s` como defaults; calibrar com a realidade do MCP depois de
   observar `step_errors` acumulado.
3. **Scraping Prometheus:** o `metrics.prom` fica na branch `data` junto dos
   snapshots; se um dia houver servidor, expor via endpoint.