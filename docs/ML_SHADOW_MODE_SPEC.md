# Spec: ML Shadow Mode (Phase 3)

> Spec-driven development (skill `spec-driven-development`). Domain spec da
> Fase 3 do `PROJECT_ROADMAP_MASTER.md` — documenta o que será construído,
> como testar e como saber que está pronto. Spec viva: atualizar antes do
> código quando decisões mudarem.

> **Status: Implemented (16/08/2026).** `services/ml/` entregue (34 testes,
> 100% cobertura), Step 5 shadow mode no pipeline (never decides), card
> "Shadow Mode" no dashboard, CI verde. Prophet/sklearn continuam plugáveis
> pela mesma interface (ver Open Questions).

## Objective

Rodar modelos de ML **em paralelo** com o pipeline heurístico atual (shadow
mode: observa e compara, **nunca decide**), para provar valor antes de
substituir a heurística:

1. **Prophet forecasting integration** → `ForecastEngine`: projeta a
   tendência do volume de erros por minuto (regressão linear por mínimos
   quadrados, determinística — Prophet real é plugável depois pela mesma
   interface, ver Open Questions).
2. **Isolation Forest anomaly detection** → `AnomalyEngine`: detecta pontos
   anômalos na série (z-score modificado robusto via mediana/MAD,
   determinístico).
3. **Side-by-side comparison (heuristic vs ML)** → `ShadowComparator`:
   compara o `risk_score` heurístico com o `ml_risk` derivado das anomalias +
   tendência; veredito `AGREE`/`DISAGREE`.
4. ~~**A/B testing framework**~~ → **fora de escopo** (decisão do usuário em
   18/08/2026): a comparação shadow registra `agreement`/`disagreement` por
   ciclo, criando o dataset de decisão; um framework formal de A/B exigiria
   tráfego real dividido, que o fluxo atual não tem — o shadow mode cumpre o
   papel de observação sem nunca decidir.

**Shadow mode = observação.** O `risk_score` e as ações do pipeline continuam
100% heurísticos. O ML só anota o snapshot.

## Tech Stack

- Python 3.11+ (stdlib puro — **zero dependências novas**; nenhum pacote de
  ML é adicionado nesta fase)
- pydantic 2.x para modelos de resultado
- pytest 9.x + pytest-cov (padrão dos serviços existentes)
- Node (Vitest) para helpers do dashboard

## Commands

```bash
# Testes do serviço (RED/GREEN)
cd services/ml && python -m pytest -q
# Cobertura
cd services/ml && python -m pytest --cov=ml --cov-report=term-missing -q
# Lint/format (CI usa exatamente estes)
python -m ruff check services/ml monitoring
python -m ruff format --check services/ml monitoring
# Pipeline completo com shadow mode
cd monitoring && python orchestrate.py --mode mock
cd monitoring && python orchestrate.py --mode real --log-file ../out/x.json
# Frontend
cd site && npm test
# Sync do dashboard (CI roda --check)
node site/scripts/sync-dashboard.mjs
```

## Project Structure

```
services/ml/ml/ml.py        → ForecastEngine, AnomalyEngine, ShadowComparator,
                              build_series, risk_from_series (fonte única)
services/ml/ml/__init__.py  → re-exports
services/ml/pyproject.toml  → setuptools, packages=["ml"]
services/ml/requirements.txt
services/ml/tests/conftest.py
services/ml/tests/test_ml.py
monitoring/orchestrate.py   → passo shadow após o passo de agregação
site/monitoring/dashboard.js + tests → helpers de exibição do shadow
docs/dashboard/assets/app.js + index.html → card "Shadow Mode"
```

## Code Style

Segue os serviços existentes: IIFE-free (Python), `var`/`from x import y`,
docstrings em inglês, nomes descritivos. Snippet:

```python
def forecast(self, series: list[float]) -> ForecastResult:
    """Project the next ``horizon`` points with least-squares linear fit."""
    xs = list(range(len(series)))
    slope, intercept = _least_squares(xs, series)
    next_x = len(series)
    predicted = [intercept + slope * (next_x + i) for i in range(self.horizon)]
    return ForecastResult(slope=slope, intercept=intercept,
                          predicted=predicted, last_value=series[-1])
```

## Testing Strategy

- **Unit tests (small, ~80%)**: cada engine com fixtures determinísticas —
  série linear perfeita (slope exato), série plana, série com 1 outlier
  óbvio, série vazia/curta demais (erro amigável), constantes (sem divisão
  por zero no MAD). Validação de entradas (`min_points`, `horizon >= 1`,
  valores finitos). **Nada de mocks** — engines são puros.
- **Integração (~15%)**: `monitoring/tests/test_orchestrate.py` — snapshot
  mock contém `shadow_mode` com `ml_risk` ∈ [0,1], `agreement` bool, e a
  heurística segue intacta (regressão guard: `risk_score` não muda).
- **Frontend (~5%)**: helpers `getShadowAgreement`/`summarizeShadow` com mock
  data.
- **Cobertura alvo:** ≥ 95% em `services/ml`.
- Regra TDD: **todo teste nasce RED antes do código** (skill
  `test-driven-development`); repetir a suíte completa antes de commitar.

## Boundaries

- **Always:** testes antes/ao lado do código; validar entradas; valores
  determinísticos (seed-free, stdlib-only); docstrings; ruff limpo; atualizar
  SPECIFICATION.md status junto com o código.
- **Ask first:** adicionar dependências de ML (sklearn/prophet) — por ora
  stdlib-only; mudar o `risk_score` heurístico; mudar o schema do snapshot
  existente (`alerts`, `comparison`).
- **Never:** shadow mode toma decisão ou altera `risk_score`; commitar
  segredos; quebrar os testes dos serviços existentes.

## Success Criteria

1. `python -m pytest -q` em `services/ml` passa com ≥ 95% de cobertura.
2. Snapshot de `orchestrate.py` (mock e real) contém `shadow_mode` válido
   (`ml_risk` ∈ [0,1], `agreement` bool, `verdict` em {AGREE, DISAGREE}).
3. `risk_score` e `alerts` do snapshot **não mudam** com o shadow ativo
   (prova do shadow mode).
4. `AnomalyEngine` acerta 100% dos outliers nos fixtures (1 outlier óbvio em
   série plana → detectado; série plana sem outlier → nenhum).
5. `ForecastEngine` reproduz exatamente a reta em série linear perfeita
   (erro < 1e-9).
6. Dashboard exibe o card "Shadow Mode" com `ml_risk`, veredito e contagem
   de anomalias; testes frontend verdes.
7. CI (`.github/workflows/test.yml`) verde: lint, format, backend, frontend.
8. `SPECIFICATION.md` §3.3 Phase 3 marcada como implementada no mesmo commit.

## Open Questions

1. **Prophet real:** instalar `prophet` (pesado, ~10 min CI) vs manter a
   regressão linear determinística? Decisão do shadow: stdlib-only agora;
   `ForecastEngine` pode trocar o fit interno sem mudar a interface.
2. **sklearn IsolationForest:** mesmo trade-off; o z-score robusto (MAD) é a
   alternativa determinística — o `AnomalyEngine` isola o algoritmo.
3. Frequência do shadow: rodar a cada ciclo (15 min) vs diário? Por ora cada
   ciclo; custo é trivial.