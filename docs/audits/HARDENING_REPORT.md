# HARDENING REPORT — Gate de entrada para a Fase 1

**Data:** 2026-08-16
**Data resolução dos bloqueadores:** 2026-08-16 (commit `34a2192`)
**Skill aplicada:** `agent-skills/skills/shipping-and-launch/SKILL.md`
**Propósito:** checklist pre-launch da Fase 0 — decidir se a Fase 0 está "pronta para ser base da Fase 1".

---

## Verdicto

**✅ PASS** — Fase 0 hardened. Os 3 bloqueadores do audit original (CI, teste do orquestrador, auditoria de dependências) foram implementados no commit `34a2192` e validados pelo próprio CI no GitHub Actions (`test.yml`, run success). Restam apenas itens de qualidade não-bloqueadores (ruff/black) para a Fase 1.

## Checklist (shipping-and-launch)

### Qualidade de código
- [x] Todos os testes passam (44/44, backend + frontend)
- [x] Cobertura ≥ meta (100% vs 80/70 exigidos)
- [x] Nenhum TODO/FIXME no código-fonte (matches só em `node_modules/`)
- [x] Nenhum `console.log` no código-fonte (matches só em `node_modules/`)
- [x] ~~Linter configurado~~ → **RESOLVIDO** (ruff 0.16.3 + `.ruff.toml` na raiz, regras E/F/I; etapas de lint e format-check no CI)
- [x] ~~Teste para `orchestrate.py`~~ → **RESOLVIDO** (12 testes em `monitoring/tests/test_orchestrate.py`, 98% coverage — linha restante é o entrypoint `__main__`)
- [x] ~~CI (`.github/workflows/test.yml`)~~ → **RESOLVIDO** (pytest ×4 + orquestrador + jest + audits em push/PR; run success em `34a2192`)

### Segurança
- [x] Zero segredos commitados
- [x] Validação de entrada via pydantic
- [x] Tooling local (`.claude/`, `.agents/`, `.codex/`, `.github/{agents,hooks,skills}`) fora do git — **corrigido nesta revisão** (`.gitignore`)
- [x] ~~`pip-audit` / `npm audit`~~ → **RESOLVIDO** (etapas no CI, `--audit-level=high` para npm)
- [x] ~~Substituir `assert` por `raise`~~ → **RESOLVIDO** (`raise ValueError` com mensagens explícitas em `orchestrate.py`; `except Exception` estreitado para `pydantic.ValidationError` em `collector.py`; constantes nomeadas em `heuristic.py`/`comparison.py`)

### Infraestrutura
- [x] Nenhuma dependência de rede (100% offline/mock) — exatamente como a SPEC pede
- [x] Logging estruturado JSON Lines (structlog) configurado
- [ ] ~~Health check HTTP~~ → N/A Fase 0 (orquestrador CLI já emite `health_check` no JSON de saída)
- [ ] ~~Deploy/Pages (`.github/workflows/deploy.yml`)~~ → **Phase 1** (ADR-006 prevê GitHub Pages)

### Documentação
- [x] README com execução e estrutura
- [x] TESTING_GUIDE com comandos reais
- [x] 10 ADRs cobrindo decisões (a expandir nesta revisão: +4 ADRs)
- [x] SERVICES_CONTRACTS para os 3 serviços
- [ ] ~~Changelog~~ → N/A (sem releases; convenção a iniciar na Phase 1)
- [ ] ~~SPEC atualizada~~ → **corrigido nesta revisão** (status + artefatos + T3.3)

### Rollback / Recovery
- [x] Git é o datastore (ADR-008) — rollback = revert de commit
- [x] Saída do pipeline ignorada (`monitoring_output.json`) — nada gerado vira lixo no repo

## Ações obrigatórias antes de fechar a Fase 1

| # | Ação | Bloqueador? | Status |
|---|---|---|---|
| 1 | Criar `.github/workflows/test.yml` (pytest ×4 serviços + jest) | ✅ Sim | ✅ Feito (`34a2192`, run success) |
| 2 | Teste para `orchestrate.py` (pipeline completo, incl. `--mode mock`) | ✅ Sim | ✅ Feito (12 testes, 98% cov) |
| 3 | `pip-audit` + `npm audit` no CI | ✅ Sim | ✅ Feito (etapas no CI) |
| 4 | Ruff/black + hook de lint | Não (qualidade) | ✅ Feito (ruff + format-check no CI) |
| 5 | Trocar `assert` por `raise` em `orchestrate.py` | Não (robustez) | ✅ Feito (valeu também p/ collector/heuristic/comparison) |
| 6 | Wrapper MCP `monitoring/mcp_salesforce.py` (ADR-007) com testes mock | ✅ Sim (Fase 1) | ✅ Feito (10 testes, 87% cov) — validação real depende de credenciais do usuário |
| 7 | `site/api/client.js` live fetcher (branch `data/`) + testes | ✅ Sim (Fase 1) | ✅ Feito (12 testes, 92% cov) |

## O que NÃO entra na Fase 1 (sem decisão explícita)

- Deploy automático (Pages) — ADR-006, aguardar UI real
- Quaisquer credenciais Salesforce/MCP — ADR-007
- Rate limiting / auth em API — inexistentes até haver API
- Mudança de arquitetura micro-serviços — ADR-001, não revisitar

---

**Referências:** SPECIFICATION.md (critérios T3.x), docs/audits/SPEC_AUDIT.md, docs/audits/REVIEW_FINDINGS.md, docs/audits/SECURITY_AUDIT.md, ADR-004 (mock-first), ADR-006 (deploy), ADR-007 (MCP).