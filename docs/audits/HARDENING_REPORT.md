# HARDENING REPORT — Gate de entrada para a Fase 1

**Data:** 2026-08-16
**Skill aplicada:** `agent-skills/skills/shipping-and-launch/SKILL.md`
**Propósito:** checklist pre-launch da Fase 0 — decidir se a Fase 0 está "pronta para ser base da Fase 1".

---

## Verdicto

**⚠️ CONDITIONAL PASS** — a Fase 0 está funcional e documentada, mas **3 itens bloqueiam** considerar o pipeline "hardened" antes da Fase 1: CI ausente, orquestrador sem teste, dependências sem auditoria. Nada bloqueia o desenvolvimento da Fase 1 em si (o código é sólido), mas estes itens devem ser o **primeiro commit da Fase 1**.

## Checklist (shipping-and-launch)

### Qualidade de código
- [x] Todos os testes passam (44/44, backend + frontend)
- [x] Cobertura ≥ meta (100% vs 80/70 exigidos)
- [x] Nenhum TODO/FIXME no código-fonte (matches só em `node_modules/`)
- [x] Nenhum `console.log` no código-fonte (matches só em `node_modules/`)
- [ ] ~~Linter configurado~~ → **Phase 1** (ruff/black)
- [ ] ~~Teste para `orchestrate.py`~~ → **BLOQUEADOR** (pipeline end-to-end sem cobertura automatizada)
- [ ] ~~CI (`.github/workflows/test.yml`)~~ → **BLOQUEADOR** (nada roda em push/PR)

### Segurança
- [x] Zero segredos commitados
- [x] Validação de entrada via pydantic
- [x] Tooling local (`.claude/`, `.agents/`, `.codex/`, `.github/{agents,hooks,skills}`) fora do git — **corrigido nesta revisão** (`.gitignore`)
- [ ] ~~`pip-audit` / `npm audit`~~ → **BLOQUEADOR** (configurar no CI da Phase 1)
- [ ] ~~Substituir `assert` por `raise`~~ → Phase 1 (baixa severidade hoje)

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

| # | Ação | Bloqueador? |
|---|---|---|
| 1 | Criar `.github/workflows/test.yml` (pytest ×4 serviços + jest) | ✅ Sim |
| 2 | Teste para `orchestrate.py` (pipeline completo, incl. `--mode mock`) | ✅ Sim |
| 3 | `pip-audit` + `npm audit` no CI | ✅ Sim |
| 4 | Ruff/black + hook de lint | Não (qualidade) |
| 5 | Trocar `assert` por `raise` em `orchestrate.py` | Não (robustez) |

## O que NÃO entra na Fase 1 (sem decisão explícita)

- Deploy automático (Pages) — ADR-006, aguardar UI real
- Quaisquer credenciais Salesforce/MCP — ADR-007
- Rate limiting / auth em API — inexistentes até haver API
- Mudança de arquitetura micro-serviços — ADR-001, não revisitar

---

**Referências:** SPECIFICATION.md (critérios T3.x), docs/audits/SPEC_AUDIT.md, docs/audits/REVIEW_FINDINGS.md, docs/audits/SECURITY_AUDIT.md, ADR-004 (mock-first), ADR-006 (deploy), ADR-007 (MCP).