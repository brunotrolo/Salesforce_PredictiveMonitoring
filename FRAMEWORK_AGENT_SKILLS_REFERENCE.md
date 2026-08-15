# FRAMEWORK: Agent Skills (SDD - Spec-Driven Development)
**Versão:** 1.0  
**Baseado em:** agent-skills by Addy Osmani  
**Uso:** Reutilizável em qualquer projeto com IA/agentes

---

## 📋 VISÃO GERAL

Framework estruturado com **6 fases** e **24 skills** para desenvolvimento com agentes de IA usando **Spec-Driven Development (SDD)**.

**Objetivo:** Evitar que a IA improvise. Estruturar um fluxo claro: especificação → planejamento → construção → testes → revisão → lançamento.

---

## 🔄 AS 6 FASES DO CICLO

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  spec  →  plan  →  build  →  test  →  review  →  ship     │
│    ↓        ↓        ↓        ↓        ↓         ↓          │
│  Req's   Tasks   Code    Tests   Audit  Ship    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📖 FASE 1: SPEC (ESPECIFICAÇÃO DE REQUISITOS)

### Objetivo
Capturar **todas as regras de negócio, casos de borda e comportamentos esperados** antes de qualquer linha de código.

### O que faz
- Inicia entrevista guiada com perguntas pontuais
- Documenta contexto do problema
- Identifica restrições e limitações
- Define critérios de sucesso
- Consolida requisitos funcionais e não-funcionais

### Entradas
```
- Contexto inicial do projeto
- Problemas a resolver
- Stakeholders e restrições
```

### Saídas
```
📄 spec.md contendo:
  ├─ Visão geral do sistema
  ├─ Requisitos funcionais (RF)
  ├─ Requisitos não-funcionais (RNF)
  ├─ Casos de uso (happy path + edge cases)
  ├─ Critérios de aceitação
  ├─ Restrições técnicas
  └─ Definição de "Done"
```

### Checklist
- [ ] Todas as perguntas respondidas
- [ ] Edge cases documentados
- [ ] Restrições técnicas mapeadas
- [ ] Critérios de sucesso definidos
- [ ] spec.md aprovado por stakeholders

---

## 📑 FASE 2: PLAN (PLANEJAMENTO E ARQUITETURA)

### Objetivo
Decompor o spec.md em **tarefas técnicas, fases de implementação e dependências**.

### O que faz
- Analisa spec.md
- Identifica dependências e ordem de implementação
- Cria arquitetura de solução
- Define fases (iterações)
- Estima esforço por tarefa
- Estabelece critérios de aceitação por fase

### Entradas
```
- spec.md (da fase anterior)
- Constraints técnicos
- Prioridades
```

### Saídas
```
📄 plan.md contendo:
  ├─ Arquitetura de solução (diagrama)
  ├─ Breakdown em fases
  ├─ Tasks por fase (tasks/phase-0.md, etc)
  ├─ Dependências entre tasks
  ├─ Timeline estimada
  └─ Métricas de sucesso por fase

📁 tasks/ pasta contendo:
  ├─ todo.md (backlog)
  ├─ phase-0.md (iteração 1)
  ├─ phase-1.md (iteração 2)
  └─ ...
```

### Checklist
- [ ] Arquitetura diagramada e aprovada
- [ ] Todas as tasks têm critérios de aceitação
- [ ] Dependências mapeadas
- [ ] Timeline realista
- [ ] Métricas de sucesso definidas

---

## 🛠️ FASE 3: BUILD (CONSTRUÇÃO / EXECUÇÃO)

### Objetivo
**Implementar o código** seguindo rigidamente o plano definido.

### O que faz
- Executa as tasks do plan.md
- Cria código fonte, testes, documentação
- Valida cada tarefa contra critérios de aceitação
- Integra com código existente
- Registra decisões de implementação

### Modos de Operação
```
1. FASE A FASE (Recomendado)
   - Execute phase-0, valide, avance para phase-1
   - Permite inspeção e ajuste contínuo
   
2. AUTO (Menos seguro)
   - Flag --auto para aprovação imediata
   - Use apenas em tarefas de baixo risco
```

### Entradas
```
- plan.md (da fase anterior)
- Tasks claras em tasks/*.md
- Ambiente pronto (dependências instaladas)
```

### Saídas
```
📄 Código implementado:
  ├─ Fonte (src/, lib/, etc)
  ├─ Testes (tests/, spec/, etc)
  ├─ Documentação (docs/)
  └─ Fixtures/mocks se necessário

📄 DECISIONS.md registrando:
  ├─ Decisões arquiteturais
  ├─ Trade-offs
  ├─ Rationale técnico
  └─ Alternativas consideradas
```

### Checklist
- [ ] Todas as tasks de phase-0 completas
- [ ] Código passa na lint (Black, Ruff, mypy, eslint, etc)
- [ ] Testes unitários escritos
- [ ] Sem warnings de compilação
- [ ] Code review passa (auto ou manual)

---

## 🧪 FASE 4: TEST (TEST-DRIVEN DEVELOPMENT / GAP CLOSING)

### Objetivo
**Fechar lacunas** de cobertura de testes antes da produção.

### O que faz
- Analisa cobertura de testes atual
- Identifica cenários não cobertos:
  - Happy path
  - Edge cases
  - Entradas inválidas
  - Exceções e erros
- Escreve testes automatizados adicionais
- Valida critérios de cobertura

### Estratégia de Cobertura
```
Pirâmide de Testes:
  ▲
  │       E2E (5-10%)
  │      /    \
  │    Integration (20-30%)
  │   /          \
  │  Unit        (60-75%)
  └─────────────────────
```

### Entradas
```
- Código implementado (phase anterior)
- Critérios de cobertura (ex: 80% backend, 70% frontend)
- Casos de teste documentados
```

### Saídas
```
📄 Cobertura expandida:
  ├─ testes/test_unit_*.py (backend)
  ├─ testes/test_integration_*.py
  ├─ e2e/test_flow_*.js (frontend)
  ├─ fixtures/ (dados de teste)
  └─ coverage_report.html

📄 GAPS_CLOSED.md documentando:
  ├─ Cenários antes não cobertos
  ├─ Testes adicionados
  ├─ Cobertura antes → depois
  └─ Riscos mitigados
```

### Checklist
- [ ] Cobertura ≥ 80% (backend) / 70% (frontend)
- [ ] Happy path coberto
- [ ] Edge cases cobertos
- [ ] Entradas inválidas testadas
- [ ] Exceções tratadas
- [ ] Teste passa (100% green)
- [ ] Performance tests (se aplicável)

---

## 👁️ FASE 5: REVIEW (REVISÃO TÉCNICA E AUDITORIA)

### Objetivo
**Auditar o código** como se fosse de outra pessoa, identificando bugs críticos e problemas de arquitetura.

### O que faz
- Assume postura de revisor externo
- Avalia:
  - Bugs críticos
  - Violações de padrão
  - Problemas de performance
  - Anti-patterns
  - Dívida técnica
- Categoriza achados por severidade
- Permite autocorreção imediata

### Critérios de Revisão
```
SEVERIDADE:
  🔴 CRÍTICO   → Bloqueia ship (segurança, corretude)
  🟠 ALTO      → Deve ser corrigido antes de ship
  🟡 MÉDIO     → Resolver antes de próxima versão
  🟢 BAIXO     → Nice-to-have, backlog
```

### Entradas
```
- Código implementado
- Testes passando
- spec.md + plan.md para contexto
```

### Saídas
```
📄 REVIEW_FINDINGS.md contendo:
  ├─ 🔴 Críticos (com fix bloqueante)
  ├─ 🟠 Alto (com sugestões)
  ├─ 🟡 Médio (backlog)
  └─ 🟢 Baixo (futura)

📊 Estatísticas:
  ├─ Total issues encontrados
  ├─ % Críticos
  ├─ % Alto
  └─ Status: Pronto para Ship? ✅/❌
```

### Checklist
- [ ] 0 issues críticos
- [ ] 0 issues alto (ou plano de correção aprovado)
- [ ] Código segue padrões do projeto
- [ ] Performance aceitável
- [ ] Logging e monitoramento em lugar
- [ ] Documentação técnica completa

---

## 🚀 FASE 6: SHIP (PRÉ-LANÇAMENTO E ENDURECIMENTO)

### Objetivo
**Preparar para produção** através de 3 subagentes especializados em paralelo.

### 3 Subagentes Paralelos

#### 1️⃣ Code Reviewer
- Validação final de qualidade de código
- Conformidade com padrões
- Detecta bugs de última hora

#### 2️⃣ Security Auditor
- Identifica vulnerabilidades
- Valida autenticação/autorização
- Revisa inputs sanitizados
- Protocolos HTTPS/TLS
- Rate limiting
- Session management

#### 3️⃣ Test Engineer
- Valida estratégia de testes
- Recomenda testes faltantes
- Prepara plano de rollback
- Define métricas de monitoramento em produção

### O que faz
- Executa análise dos 3 subagentes
- Consolida achados
- Prioriza bloqueios críticos
- Gera checklist de pré-lançamento

### Entradas
```
- Código + testes (fases anteriores)
- Review findings (resolvidos)
- Environment de staging
```

### Saídas
```
📄 HARDENING_REPORT.md contendo:

1. CODE QUALITY
   ├─ % Cobertura
   ├─ Linhas de código
   ├─ Complexidade ciclomática
   └─ Issues restantes

2. SECURITY CHECKLIST
   ├─ Autenticação: ✅/❌
   ├─ Rate limiting: ✅/❌
   ├─ Input validation: ✅/❌
   ├─ HTTPS/TLS: ✅/❌
   ├─ Session security: ✅/❌
   ├─ CORS headers: ✅/❌
   ├─ Password hashing: ✅/❌
   ├─ Secrets management: ✅/❌
   └─ ...

3. ROLLBACK PLAN
   ├─ Procedimento de rollback
   ├─ Fallback strategy
   ├─ Data migration plan
   └─ Communication plan

4. MONITORING & ALERTS
   ├─ Métricas key (latência, erros, CPU, memória)
   ├─ Alertas configurados
   ├─ Dashboard de observabilidade
   └─ On-call playbook

5. GO/NO-GO DECISION
   ├─ Status: GO ✅ / NO-GO ❌
   ├─ Bloqueadores (se houver)
   └─ Data de lançamento recomendada
```

### Checklist
- [ ] Code review: 0 críticos
- [ ] Security audit: Todos pontos resolvidos
- [ ] Test coverage: ≥ mínimo esperado
- [ ] Monitoramento pronto
- [ ] Rollback plan documentado
- [ ] Team de on-call treinado
- [ ] Comunicação aprovada
- [ ] Status: **GO** ✅

---

## 💡 GUIA DE BOAS PRÁTICAS

### 1. Não Pule a Fase de Spec
**Por quê:** O objetivo do SDD é evitar que a IA gaste tokens em código com premissas incorretas.

**Como:**
```
✅ Investir tempo em spec.md é economizar semanas de refatoração
✅ Regras de negócio complexas devem estar claras ANTES de código
✅ Consultar stakeholders na fase de spec, não após code pronto
```

### 2. Construção Iterativa vs. Modo Auto
**Recomendação:** Fase a fase (não --auto).

**Por quê:**
```
✅ Permite inspeção intermediária
✅ Evita refações extensas
✅ Detecta problemas cedo
❌ --auto só para tarefas de baixo risco
```

### 3. Cross-Review Entre Modelos
**Para revisões críticas (review/ship):**

```
1. Modelo A gera código (ex: Claude)
2. Exporte código + plan
3. Submeta a Modelo B (ex: GPT-4) para review
→ Evita "cegueira por confirmação"
```

### 4. Documentar Decisões Arquiteturais
**Sempre:**
```
📄 DECISIONS.md registrando:
  ├─ O que foi decidido
  ├─ Por que foi decidido (contexto)
  ├─ Alternativas consideradas
  ├─ Trade-offs
  └─ Data e autor
```

### 5. Priorizar Segurança no Ship
**Atenção redobrada:**
```
🔴 CRÍTICO (Não lançar sem resolver):
  ├─ Rate limiting
  ├─ Session integrity
  ├─ Input sanitization
  ├─ HTTPS enforcement
  ├─ Secret management
  └─ Autenticação/Autorização
```

### 6. Métricas de Sucesso por Fase
**Definir no plano:**
```
Phase 0:
  ├─ Arquitetura aprovada: ✅
  ├─ Scaffold 80%+: ✅
  └─ Testes rodando: ✅

Phase 1:
  ├─ Features core 100%: ✅
  ├─ Cobertura 70%+: ✅
  └─ Integração pronta: ✅
```

---

## 🔧 IMPLEMENTAÇÃO DO FRAMEWORK

### Passo 1: Preparar o Ambiente
```bash
# Estrutura de pastas sugerida
project/
├── spec.md                 # Saída de SPEC
├── plan.md                 # Saída de PLAN
├── DECISIONS.md            # Decisões arquiteturais
├── src/                    # Código (PHASE BUILD)
├── tests/                  # Testes (PHASE TEST)
├── tasks/
│   ├── todo.md
│   ├── phase-0.md
│   ├── phase-1.md
│   └── ...
└── docs/
    ├── REVIEW_FINDINGS.md  # Saída de REVIEW
    ├── HARDENING_REPORT.md # Saída de SHIP
    └── ...
```

### Passo 2: Executar Ciclo Completo
```
1. /spec       → Gera spec.md
2. /plan       → Gera plan.md + tasks/*.md
3. /build      → Implementa phase-0, valida, phase-1, valida...
4. /test       → Fecha gaps de teste até ≥80%
5. /review     → Audita código, gera REVIEW_FINDINGS.md
6. /ship       → 3 subagentes, gera HARDENING_REPORT.md, GO/NO-GO
```

### Passo 3: Validar Critérios de Saída
```
✅ Cada fase tem checklist
✅ Saída de cada fase é entrada da próxima
✅ Documentação rastreável
✅ Decisões registradas
```

---

## 📊 MATRIZ DE RASTREABILIDADE

```
spec.md
  ├─ Requisitos Funcionais (RF)
  │   └─> plan.md (Tasks que implementam RF)
  │       └─> src/ (Código implementado)
  │           └─> tests/ (Testes validam RF)
  │               └─> REVIEW_FINDINGS.md (Auditoria)
  │                   └─> HARDENING_REPORT.md (Ship decision)
  │
  ├─ Requisitos Não-Funcionais (RNF)
  │   └─> plan.md (Tasks de arquitetura)
  │       └─> docs/ARCHITECTURE.md
  │           └─> REVIEW_FINDINGS.md (Performance, Security)
  │
  └─ Critérios de Aceitação
      └─> tests/ (Cada critério tem teste)
          └─> coverage report (100% cobertura)
```

---

## 🎯 QUANDO USAR ESTE FRAMEWORK

✅ **Recomendado para:**
- Projetos com especificação complexa
- Desenvolvimento com agentes de IA
- Projetos onde especificação evita refatoração
- Produtos que exigem auditoria (compliance, segurança)
- Equipes distribuídas

❌ **Não recomendado para:**
- Scripts únicos e descartáveis
- Protótipos de 1 dia
- Tarefas muito simples

---

## 📚 RESUMO VISUAL

```
FASE          ENTRADA              PROCESSO             SAÍDA
─────────────────────────────────────────────────────────────
spec          Contexto             Entrevista           spec.md
              Problema             Consolidar req's     Requisitos

plan          spec.md              Arquitetar           plan.md
                                   Decompor             tasks/*.md

build         plan.md              Implementar          src/
              tasks/*.md           Code + tests         tests/

test          src/ + tests/        Gap closing          coverage
                                   Testes adicionais    ≥80%

review        Código               Auditar              REVIEW_
              Completo             3 perspectivas       FINDINGS.md

ship          Código               3 subagentes        HARDENING_
              + review             paralelos           REPORT.md
                                                        GO/NO-GO
```

---

## 🔗 RECURSOS

- **Agent Skills:** https://github.com/addyosmani/agent-skills
- **SDD Concept:** Spec-Driven Development (Addy Osmani, Google Chrome)
- **Framework Version:** 1.0 (2026-08-15)

---

**Próximo:** Use este framework como referência agnóstica em seus projetos. Adapte as fases e skills conforme necessário.
