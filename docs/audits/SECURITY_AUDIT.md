# SECURITY AUDIT — Fase 0

**Data:** 2026-08-16
**Skill aplicada:** `agent-skills/skills/security-and-hardening/SKILL.md`
**Escopo:** Fase 0 (mock-first) — código, dependências, segredos, .gitignore
**Modelo:** STRIDE

---

## Verdicto

**PASS para a Fase 0** — sem segredos, sem dados reais, validação de entrada presente. Riscos reais só começam na Fase 1 (conexão real com Salesforce via MCP), com mitigação já decidida no ADR-007.

## Análise STRIDE

| Ameaça | Risco (Fase 0) | Justificativa |
|---|---|---|
| **Spoofing** | N/A | Sem autenticação — dados 100% mock gerados localmente (`mock_logs.yaml`, `generate_mock_logs()`). |
| **Tampering** | BAIXO | Dados mock locais; arquivo de saída `monitoring_output.json` é local e ignorado pelo git. |
| **Repudiation** | ✅ MITIGADO | `logger.py` configura structlog JSON Lines com timestamps ISO — trilha de auditoria desde o início. |
| **Info Disclosure** | ✅ OK | Zero segredos no repo (verificado em código + gitignore). Saída ignorada (`monitoring_output.json`). |
| **DoS** | N/A (Phase 5) | Sem rede, sem servidor. |
| **Elevation of Privilege** | N/A | Script local, sem privilégios especiais. |

## Checklist security-and-hardening

- ✅ **Nenhum segredo commitado**: `git ls-files` mostra apenas código; `.env`, `.venv/`, `venv/` ignorados; nenhuma credencial em código-fonte.
- ✅ **Validação de entrada**: pydantic em todos os serviços (`SalesforceLog(**log)`), com `validate()` no collector reportando erros por índice.
- ⚠️ `except Exception` (collector.py:31) — pega erros de programação junto com validação; preferir `pydantic.ValidationError` (BAIXO risco, corrigir na Phase 1).
- ⚠️ `assert` (orchestrate.py:85-88) — checagem de runtime removível com `-O`; trocar por `raise` (MÉDIA).
- ⚠️ **Dependências sem auditoria**: `pip-audit` / `npm audit` não rodados e não configurados. Fase 0 usa só dev deps (pytest, jest, pydantic, structlog, faker) — risco baixo, mas **gate Phase 1** (deps de runtime da Tiops/Salesforce entram aí).
- ⚠️ **Tooling local no disco (não versionado, não ignorado)**: `.claude/` (25 skills + `settings.local.json` com hooks), `.agents/`, `.codex/` (hooks.json), `.github/agents|hooks|skills` (pack impeccable p/ Copilot). São instalações locais de máquina, **não devem entrar no repo** — ver ação no `.gitignore`.

## .gitignore — estado atual (gap real)

Arquivos de tooling local **não estão ignorados**:

```
.claude/
.agents/
.codex/
.github/agents/
.github/hooks/
.github/skills/
```

Risco: `git add .` em um momento descuidado versiona `settings.local.json` (máquina-específico) e packs duplicados. Correção aplicada nesta revisão (ver `git diff .gitignore` no commit).

## Fase 1 — requisitos de segurança (gate)

1. `TIOPS_API_KEY` (ou credencial MCP) via variável de ambiente / secrets — nunca em código (ADR-007 já decide MCP over OAuth direto)
2. `pip-audit` + `npm audit` no CI
3. Substituir `assert` por `raise`
4. `except pydantic.ValidationError` específico
5. Validar que `.claude/`, `.agents/`, `.codex/` continuam ignorados após novas instalações