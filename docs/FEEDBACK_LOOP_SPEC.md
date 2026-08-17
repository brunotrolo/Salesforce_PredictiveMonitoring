# Spec: Feedback Loop (Phase 4)

> Spec-driven development (skill `spec-driven-development`). Domain spec da
> Fase 4 do `PROJECT_ROADMAP_MASTER.md` — documenta o que será construído,
> como testar e como saber que está pronto. Spec viva: atualizar antes do
> código quando decisões mudarem.

## Objective

Fechar o ciclo de feedback do **ML shadow mode** (Fase 3): hoje o ML observa e
compara (`shadow_mode` no snapshot), mas ninguém mede se ele acertou, e não há
caminho para o usuário dizer "esse sinal era falso positivo". A Fase 4 adiciona
três capacidades, todas **observacionais — nenhuma decide**:

1. **Model accuracy tracking** → `AccuracyTracker`: avalia o `shadow_mode` do
   snapshot anterior contra a série real do snapshot atual. Responde: "a direção
   prevista se confirmou?" e "a anomalia sinalizada foi seguida de pico?".
2. **User feedback ingestion** → `FeedbackStore`: carrega e valida um arquivo
   `feedback.json` (alimentado pelo usuário, ex.: via issue/PR na branch data)
   e agrega ações `true_positive`/`false_positive` por alvo
   (`anomaly`/`alert`).
3. **Weekly retraining** → `Calibrator` + CLI: como os engines da Fase 3 são
   determinísticos (regressão linear + z-score, sem pesos treináveis), o
   "retraining" honesto é **calibrar o threshold** do `AnomalyEngine` a partir
   do histórico de falsos positivos observados. O Calibrator recomenda um novo
   threshold; a aplicação é decisão explícita (open question).

Sucesso: o snapshot ganha `accuracy` (quando há snapshot anterior) e
`feedback_summary` (quando há arquivo); o dashboard mostra o card "Acurácia ML";
o usuário sabe, por coleta, se o ML está acertando — sem que isso mude
`risk_score`/`alerts`.

## Tech Stack

- Python 3.11+ (stdlib puro — **zero dependências novas**; pydantic como os
  demais serviços), pytest + pytest-cov, ruff.
- Frontend: Vanilla JS (jest), espelhado via `site/scripts/sync-dashboard.mjs`.

## Commands

```bash
# Serviço (TDD)
cd services/feedback
python -m pytest -q --cov=feedback --cov-report=term-missing
python -m ruff check feedback tests
python -m ruff format feedback tests

# CLI do retraining (weekly v1)
python -m feedback.calibrate --samples samples.json --target 0.2

# Pipeline
python -m pytest monitoring -q            # de monitoring/
python orchestrate.py --mode mock --history-file prev.json --feedback-file feedback.json

# Frontend
cd site && npm test
node site/scripts/sync-dashboard.mjs      # espelha assets no docs/dashboard
```

## Project Structure

```
services/feedback/
  pyproject.toml        → monitoring-feedback 0.1.0 (pacote "feedback")
  requirements.txt      → pytest/pytest-cov/pydantic/structlog/faker/ruff (sem -e .)
  feedback/
    __init__.py         → exporta AccuracyTracker, FeedbackStore, Calibrator, modelos
    feedback.py         → engines (AccuracyTracker, FeedbackStore, Calibrator)
    calibrate.py        → CLI do retraining (python -m feedback.calibrate)
  tests/
    conftest.py         → fixtures (prev/current snapshots, feedback samples)
    test_feedback.py    → contratos e bordas (100% cobertura)
monitoring/orchestrate.py → Steps 6 (accuracy) e 7 (feedback), flags opcionais
monitoring/tests/test_orchestrate.py → TestFeedbackLoop
site/monitoring/dashboard.js + tests → summarizeAccuracy/getAccuracyVerdict
site/monitoring/mock-data.js → accuracy realista nos mocks
docs/dashboard/assets/app.js + index.html → card "Acurácia ML"
docs/FEEDBACK_LOOP_SPEC.md (este) → spec viva
```

## Code Style

Mesmo padrão de `services/ml` (pydantic BaseModel + módulo único):

```python
class AccuracyResult(BaseModel):
    status: str = "no_data"           # "evaluated" | "no_data"
    direction_expected: str | None    # "up" | "down" | "flat" (slope previsto)
    direction_actual: str | None      # direção observada na série real
    forecast_hit: bool | None         # direção prevista == observada
    anomaly_flagged: bool = False     # anomalia foi sinalizada no anterior
    anomaly_hit: bool | None          # sinal seguido de pico real?
    false_positive: bool = False      # sinalizado sem pico
    series_actual: list[float] = []
```

Convenções: `var` é JS, aqui Python — módulo único `feedback.py`, namespaces
por classe, docstrings concisas (linha única quando possível), sem imports
mortos, `model_dump()` para serializar.

## Testing Strategy

- **Unit (services/feedback):** pytest, 100% cobertura exigida. Contratos de
  borda: snapshot anterior sem `shadow_mode` → `no_data`; série atual vazia →
  `no_data`; direção `flat` (slope ≈ 0) → não é hit nem miss; anomalia sem pico
  → `false_positive`; feedback.json com linhas inválidas → ignoradas com contagem;
  arquivo inexistente → `FileNotFoundError` claro; Calibrator com menos de
  `min_samples` → `insufficient`; fp alto → threshold sobe; fp baixo → desce;
  clamp no intervalo `[2.0, 6.0]`; determinismo.
- **Integration (monitoring):** pipeline com `history` contendo `shadow_mode` →
  `accuracy` no resultado; com `--feedback-file` → `feedback_summary`; mock sem
  nada disso → chaves ausentes (sem quebra).
- **Frontend (site):** `summarizeAccuracy` (fallback `no_data`), veredito
  legível, mock data com accuracy.

## Boundaries

- **Always:** testar antes de commitar; `sync-dashboard.mjs` antes do commit;
  `ruff format` + `check`; docstrings em PT/EN no estilo existente; nada de
  segredos.
- **Ask first:** mudar `.github/workflows/*` (o collect.yml continuar passando
  `--history-file`; o `--feedback-file` na produção e o cron semanal do
  retraining ficam como open questions); adicionar dependências.
- **Never:** aplicar o threshold calibrado sem decisão explícita; mexer no
  `risk_score`/`alerts`; commitar sem CI verde.

## Success Criteria

1. `services/feedback` com 100% cobertura; suíte completa do repo verde
   (pytest services/ml monitoring + npm test + sync `--check`).
2. Pipeline mock com `--history-file` (snapshot com `shadow_mode`) →
   `result["accuracy"]` com `status == "evaluated"`, direção e hits coerentes
   com o mock (série plana → `forecast_hit` verdadeiro ou definido).
3. Pipeline mock com `--feedback-file` → `result["feedback_summary"]` com
   contagens por ação; arquivo com linha inválida não quebra o pipeline.
4. Dashboard: card "Acurácia ML" renderiza de snapshot com accuracy; helpers
   testados no jest; sync atualizado.
5. `SPECIFICATION.md` §3.3 Phase 4 e `PROJECT_ROADMAP_MASTER.md` marcadas
   implementadas no mesmo commit.

## Open Questions

1. **Coleta do feedback em produção:** o `--feedback-file` no `collect.yml`
   exigiria baixar `feedback.json` da branch `data` antes de rodar o pipeline
   (mudança de workflow). Por ora o flag existe no pipeline; a integração no
   workflow é decisão explícita.
2. **Aplicar a calibração:** o Calibrator recomenda; quem aplica o novo
   threshold e quando (manual semanal? cron com auto-aplicação?) — v1 entrega
   só a recomendação via CLI.
3. **Direção "flat" conta como hit?** v1: `flat` não pontua nem como hit nem
   como miss (indeterminado) — documentado nos testes.