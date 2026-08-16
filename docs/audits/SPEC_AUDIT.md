# SPEC AUDIT — SPECIFICATION.md vs. spec-driven-development

**Data:** 2026-08-16
**Skill aplicada:** `agent-skills/skills/spec-driven-development/SKILL.md`
**Escopo:** SPECIFICATION.md (v1.0, 2026-08-15) e conformidade da Fase 0 entregue no commit `ddbdab9`

---

## Resumo executivo

A SPEC existe, está versionada, tem critérios de aceite testáveis e comandos executáveis — o núcleo do SDD está presente. Porém a spec **não foi mantida viva**: está com status pré-execução quando a Fase 0 já foi implementada, e declara 9 artefatos quando apenas 7 existem no repo. Verdicto: **PASS com ressalvas** — correções listadas abaixo.

## Checklist por área da skill

| Área exigida pela skill | Status | Evidência / Lacuna |
|---|---|---|
| 1. Objective | ✅ | Seção 1: artefatos obrigatórios + critérios mensuráveis |
| 2. Commands (executáveis) | ⚠️ | T3.1/T3.2/T3.3 existem; T3.3 aponta `/tmp/monitoring.log` mas a Fase 0 escreve `monitoring_output.json` |
| 3. Project Structure | ✅ | Seções 3.1 (deliverables) e 4.2 (tree de micro-serviços) |
| 4. Code Style (snippet real) | ❌ | Nenhum snippet de código ou convenção de estilo definida na spec |
| 5. Testing Strategy | ✅ | T3.1 (pytest+cov), T3.2 (Jest+cov), limites 80%/70% |
| 6. Boundaries (Always/Ask/Never) | ❌ | Nenhuma seção de limites explícita na spec |
| Capability map (Phase 0) | ❌ | Fase 0 agrupa backend + frontend + pipeline + docs sem mapa de módulos/ordem de build |
| Spec é living document | ❌ | Status diz "VALIDADO PARA EXECUÇÃO" / "PRONTO PARA PHASE 0 KICKOFF" — Fase 0 já implementada (commit `ddbdab9`) |
| Spec commitada | ✅ | `SPECIFICATION.md` no commit `ddbdab9` |

## Achados detalhados

### F-01 (ALTA) — Spec desatualizada: Fase 0 implementada, spec diz "pronto para kickoff"
A spec (linha 5, seções 9 e resumo) declara status pré-execução. A Fase 0 foi implementada, testada (44/44 testes, 100% coverage) e commitada. A skill exige que a spec seja atualizada quando o escopo muda — a spec deveria marcar Fase 0 como **IMPLEMENTED** e mover o foco para Fase 1.

### F-02 (ALTA) — Artefatos declarados ✅ que não existem
Seção 1.1 declara 9 artefatos "✅ COMPLETO", mas **`DELIVERY_SUMMARY.md` (A7) e `PREDICTIVE_MONITORING_PLAN.md` (A8) não existem no repo**. Artefatos reais: 7 (README, SPECIFICATION, PROJECT_ROADMAP_MASTER, 5 docs em `docs/`). As métricas "4,009 linhas / 9 arquivos" estão infladas.

### F-03 (MÉDIA) — Sem seção Code Style nem Boundaries
A skill pede um snippet real de estilo e a tríade Always/Ask-first/Never. A spec não define convenções de código (naming, formatação) nem limites ("nunca commitar segredos", "pedir antes de mudar CI", etc.). Os limites hoje só existem implicitamente no repo (`.gitignore`).

### F-04 (MÉDIA) — Sem capability map para a Fase 0
A Fase 0 é uma iniciativa com várias capacidades independentemente testáveis (backend, frontend, pipeline, docs). A skill recomenda um mapa de módulos + ordem de build antes de especificar. Na prática os módulos existem (services/, site/, monitoring/) e foram construídos na ordem certa, mas o mapa nunca foi registrado.

### F-05 (BAIXA) — Divergência de caminho no T3.3
`TESTE T3.3` espera JSON em `/tmp/monitoring.log`; a implementação escreve `monitoring_output.json` na raiz (documentado em `docs/TESTING_GUIDE.md`). A spec e o teste divergem.

## Passou com louvor

- ✅ Critérios de sucesso **específicos e testáveis** (80%/70% coverage, comandos, contagens)
- ✅ Cobertura real **supera** a meta: 100% backend + 100% frontend (44/44 testes)
- ✅ Zero dependência Salesforce na Fase 0, como especificado (mock-first, ADR-004)
- ✅ Transição Fase 0 → Fase 1 é de fato mínima (só o collector muda)

## Ações recomendadas

| # | Ação | Prioridade |
|---|---|---|
| 1 | Atualizar status da SPEC para Fase 0 IMPLEMENTED + Fase 1 NEXT | Alta |
| 2 | Corrigir tabela de artefatos (7 reais) e métricas de linhas | Alta |
| 3 | Adicionar seção Code Style + Boundaries (snippet + tríade) | Média |
| 4 | Registrar capability map da Fase 0 (retroativamente, via ADR) | Média |
| 5 | Alinhar T3.3 ao caminho real (`monitoring_output.json`) | Baixa |