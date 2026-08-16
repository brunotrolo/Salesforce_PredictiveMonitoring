# REVIEW FINDINGS — Fase 0 (Código + Estrutura)

**Data:** 2026-08-16
**Skill aplicada:** `agent-skills/skills/code-review-and-quality/SKILL.md`
**Escopo:** commit `ddbdab9` (43 arquivos, 9.687 linhas) — services/, site/, monitoring/, docs/
**Método:** leitura direta dos 5 arquivos Python (collector, heuristic, comparison, logger, orchestrate) + configs (pytest.ini ×4, jest.config.js, package.json) + auditoria de estrutura de commit.

---

## Eixo 1 — Escopo e Estrutura de Commit

| Achado | Severidade | Detalhe |
|---|---|---|
| Commit único gigante (9.687 linhas) | MÉDIA | `ddbdab9` mistura backend, frontend, pipeline, docs e tooling. A skill recomenda commits atômicos (100–1000 linhas). Aceitável como commit inicial de scaffold, mas **daqui em diante**: conventional commits por unidade lógica. |
| Estrutura de pastas limpa | ✅ | `services/<nome>/{src,tests,pytest.ini,requirements.txt}` + `site/` + `monitoring/` + `docs/` — padronizada e previsível. |
| `docs/audits/` novo | ✅ | Artefatos desta revisão agrupados em subpasta própria — não polui a doc raiz do projeto. |

## Eixo 2 — Correção / Lógica

| Arquivo | Achado | Severidade |
|---|---|---|
| `orchestrate.py:85-88` | `assert` para validação de runtime — **removido com `python -O`**. Deveria ser `if not ...: raise ValueError`. | MÉDIA |
| `orchestrate.py:12-15` | `sys.path.insert` para importar serviços — funciona, mas é frágil (depende de layout relativo) e esconde o acoplamento. Alternativa Phase 1+: empacotar serviços (pip install -e) ou pyproject. | MÉDIA → ✅ RESOLVIDO (ADR-016, editable installs) |
| `orchestrate.py:42` | `l.model_dump() if hasattr(l, 'model_dump') else l.__dict__` — `hasattr` sempre verdadeiro (pydantic v2); é código morto/defensivo desnecessário. | BAIXA |
| `heuristic.py:21,24` | Magic numbers: threshold `1000ms`, pesos `0.3`/`0.2`. Devem virar constantes nomeadas (fácil de parametrizar no Phase 2 com ML). | BAIXA |
| `comparison.py:31-42` | Thresholds `0.3`/`0.1` hard-coded. Mesma recomendação. | BAIXA |
| `collector.py:31` | `except Exception` — pega tudo, inclusive erros de programação. Preferir `pydantic.ValidationError`. | BAIXA |
| `orchestrate.py:22` | Mock usa `datetime.now(timezone.utc)` — ok; timestamp ISO correto. | ✅ |

## Eixo 3 — Estilo e Consistência

- ✅ `from __future__ import annotations` + type hints em todos os módulos.
- ✅ pydantic `BaseModel` nos três serviços — contratos tipados.
- ✅ Nomes consistentes (`LogCollector`, `HeuristicEngine`, `ComparisonService`).
- ✅ `src/` renomeado para pacote por serviço (`services/<domain>/<domain>/`) via ADR-016 (editable installs).
- ⚠️ Sem linter/formatter configurado (ruff/black) — Phase 1.
- ⚠️ Docstrings resumidas; sem exemplos de uso (aceitável para mock, melhorar na Phase 1).

## Eixo 4 — Documentação

- ✅ `docs/` extensa: TESTING_GUIDE, SERVICES_CONTRACTS, FASE_0_IMPLEMENTATION_GUIDE, ARCHITECTURE_DECISIONS (10 ADRs), PHASE_0_QUICK_REFERENCE.
- ✅ README cobre execução e estrutura.
- ⚠️ `docs/CLAUDE_CODE_SKILLS.md` e `FRAMEWORK_AGENT_SKILLS_REFERENCE.md` duplicam informação do pack `agent-skills/` — manter apenas referências, não conteúdo (evitar drift).
- ⚠️ SPEC desatualizada (ver `docs/audits/SPEC_AUDIT.md` F-01/F-02).

## Eixo 5 — Testes

| Item | Status | Detalhe |
|---|---|---|
| Backend | ✅ | 4 suítes (collector, comparison, heuristic, logger), 26 testes, coverage 100% (meta 80%) |
| Frontend | ✅ | 1 suíte (`site/monitoring/tests/test-dashboard.js`), 18 testes, coverage 100% (meta 70%) |
| Config por serviço | ✅ | `pytest.ini` com `pythonpath = src` + `--cov=src` em cada serviço |
| Fixtures | ✅ | `tests/fixtures/mock_logs.yaml` + conftest por serviço |
| **orchestrate.py SEM teste** | **ALTA** | O pipeline completo (imports via sys.path + `run_pipeline()`) não tem teste automatizado — só smoke manual. Se quebrar, nenhum CI pega. |
| Jest ESM | ✅ | `npx --node-options=--experimental-vm-modules jest --coverage` — workaround Windows documentado no package.json |
| CI | ❌ | `.github/workflows/` vazio — nenhum teste roda automaticamente (ver HARDENING_REPORT) |

## Priorização

| Prioridade | Ação |
|---|---|
| ALTA | Adicionar teste para `orchestrate.py` (pipeline end-to-end) — gate Phase 1 |
| ALTA | CI workflows (`test.yml`) — gate Phase 1 |
| MÉDIA | Trocar `assert` por `raise` em orchestrate.py |
| MÉDIA | Commit atômico + conventional commits daqui em diante |
| BAIXA | Constantes nomeadas para thresholds/pesos |
| BAIXA | `except pydantic.ValidationError` em collector.py |
| BAIXA | Remover `hasattr` morto em orchestrate.py:42 |
| BAIXA | Ruff/black no Phase 1 |