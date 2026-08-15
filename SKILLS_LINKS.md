# SKILLS RECOMENDADAS - LINKS E COMO USAR
**Projeto:** Salesforce Predictive Monitoring  
**Data:** 2026-08-15

---

## 📌 SKILLS DISPONÍVEIS (Claude Code)

As skills do Claude Code são acessadas via **slash commands** dentro da interface Claude Code. Aqui está como acessar cada uma:

---

## 1. `/code-review` ⭐ CRÍTICA

### O que faz:
Revisa código para bugs, performance, test coverage, simplificações.

### Como usar:
```
/code-review                    # Revisa diff atual (low effort por padrão)
/code-review low                # Esforço baixo (rápido, high confidence)
/code-review medium             # Esforço médio (balanceado)
/code-review high               # Esforço alto (análise completa)
/code-review --comment          # Posta findings como comentários inline na PR
```

### Quando usar (Projeto):
- **Fase 0:** Antes de merge de `services/collector/`, `services/heuristic/`
- **Fase 1:** Validar integração MCP
- **Fase 3:** HIGH effort para `services/comparison/` (Prophet + Isolation Forest)
- **Todas as fases:** Toda PR de backend

### Exemplo prático:
```bash
# Terminal
git checkout -b feature/heuristic-v2
# ... escreve código ...
git add services/heuristic/src/heuristic.py

# No Claude Code:
/code-review medium --comment
# Vai revisar o diff, postar findings inline, você aplica sugestões
```

---

## 2. `/dataviz` ⭐ CRÍTICA PARA FRONTEND

### O que faz:
Design de visualizações (cores, charts, acessibilidade, responsividade).

### Como usar:
```
/dataviz
```
(Descreva o componente que quer desenhar)

### Quando usar (Projeto):
- **Fase 0:** 1x (design do monitoring dashboard)
  - Risk score gauge (0-1)
  - Line chart (histórico 30 dias)
  - Alerts panel (severity badges)
  - Health check banner

### Exemplo prático:
```
Usuário (no Claude Code):
  "Preciso de um dashboard com:
   - Gauge circular para risk_score (0-1, cores: verde/amarelo/vermelho)
   - Line chart com 30 dias de histórico
   - Alert badges (CRÍTICA=red, ALTA=orange, MÉDIA=yellow, BAIXA=gray)
   - Responsivo: mobile (375px), tablet (768px), desktop (1920px)
   - Dark mode support"

Claude (via /dataviz):
  ✓ Paleta de cores validada (light/dark)
  ✓ Chart recommendations
  ✓ Layout grid + breakpoints
  ✓ Accessibility checklist (WCAG 2.1 AA)
  ✓ Contrast ratios validados
```

---

## 3. `/simplify` ⭐ IMPORTANTE PARA CÓDIGO LIMPO

### O que faz:
Refactora código para eliminar duplicação, simplificar logic, melhorar eficiência.

### Como usar:
```
/simplify
```
(Executa no diff atual)

### Quando usar (Projeto):
- **Fase 0:** Antes de escrever `services/heuristic/src/heuristic.py`
- **Fase 1:** Limpeza geral de transformação Pandas
- **Fase 3:** Antes de `services/comparison/` (ML logic pode ficar complexa)
- **Fase 4:** Cleanup de `weekly_retrain.py`

### Exemplo prático:
```python
# Antes (repetitivo):
def analyze(logs):
    for log in logs:
        if log['status_code'] >= 500:
            errors.append(log)
    
    for log in logs:
        if log['duration_ms'] > 1000:
            slow.append(log)
    
    for log in logs:
        if log['status_code'] >= 500 and log['duration_ms'] > 1000:
            critical.append(log)

# No Claude Code:
/simplify
# Resultado:
def analyze(logs):
    errors = [l for l in logs if l['status_code'] >= 500]
    slow = [l for l in logs if l['duration_ms'] > 1000]
    critical = [l for l in logs if l['status_code'] >= 500 and l['duration_ms'] > 1000]
    # Ou melhor ainda:
    critical = [l for l in logs if l['status_code'] >= 500 and l['duration_ms'] > 1000]
    errors = [l for l in logs if l['status_code'] >= 500 and l not in critical]
    # E assim por diante...
```

---

## 4. `/loop` (Opcional, para monitoramento)

### O que faz:
Executa um comando/prompt repetidamente em intervalo.

### Como usar:
```
/loop 5m /seu-comando-aqui
/loop 10m /seu-prompt-aqui
```

### Quando usar (Projeto):
- **Fase 0 APENAS:** Para validar que workflow roda continuamente
  ```
  /loop 5m
  Verifique se o último workflow `monitoring-collect.yml` rodou com sucesso
  nos últimos 5 minutos, validando coleta + JSON output
  ```

### Exemplo prático:
```bash
# Fase 0: Validar workflow por 1 hora
/loop 5m
  Rodar: git log --oneline -1 && git show --stat
  Verificar: 
    - Último commit foi há < 10 minutos?
    - Commit contém "monitoring/data/" files?
    - Logs mostram execução bem-sucedida?
```

---

## 5. `/claude-api` (Opcional, Fase 5+)

### O que faz:
Referência de Claude API (models, pricing, features, SDKs).

### Como usar:
```
/claude-api
```
(Descreva o que quer fazer com Claude API)

### Quando usar (Projeto):
- **Fase 5 APENAS:** Se decidir usar Claude para análise inteligente
  - Exemplo: LLM analisa logs anômalos e sugere causa raiz
  - Exemplo: Claude refina thresholds da heurística baseado em histórico

### Não aplicável agora (Fase 0-4)

---

## 6. `/artifact-design` (Opcional, para mockups)

### O que faz:
Design guidance para artifacts (documentos, mockups, diagramas).

### Quando usar (Projeto):
- **Fase 0:** Se quiser criar mockup interativo do dashboard
- **Fase 2+:** Se quiser artifact com charts interativos

### Não recomendado para código real (use /dataviz em vez disso)

---

## 7. Outras Skills Não Aplicáveis

```
❌ /derivatives-specialist-skill     (trading, não relevante)
❌ /morning                          (briefing diário, não projeto)
❌ /web-artifacts-builder            (artifacts complexos, não precisamos)
❌ /session-start-hook               (automação web session, opcional)
```

---

## 📋 SKILLS POR FASE

### Fase 0 (Scaffold + Testes com Mocks)
```
/code-review low                      # Validar estrutura inicial
/dataviz                              # Design dashboard mockup
/loop 5m (monitor workflow)           # Validar execução contínua
```

### Fase 1 (Coleta Real + Heurística)
```
/code-review medium                   # PR de collector + heuristic
/dataviz (refinement)                 # Ajustar dashboard com dados reais
/simplify                             # Limpar heuristic.py se necessário
```

### Fase 2 (Alertas + Notificações)
```
/code-review medium                   # Notification logic
/dataviz                              # Severity colors no dashboard
```

### Fase 3 (Modo Sombra ML)
```
/code-review high                     # Prophet + Isolation Forest
/simplify                             # Refactor comparison logic
```

### Fase 4 (Feedback Loop)
```
/code-review medium                   # Retrain logic
/dataviz (refinement)                 # Feedback UX
```

### Fase 5 (Hardening)
```
/code-review high                     # Error handling + retry
/simplify                             # Cleanup geral
/claude-api (opcional)                # Se usar LLM
```

---

## 🎯 COMO ACESSAR AS SKILLS

### 1. No Claude Code (Web ou Desktop)
```
Abra a interface Claude Code
Digite: /code-review
Pressione Tab ou Enter para sugestões
Escolha a skill desejada
```

### 2. No Claude Code CLI
```bash
claude code --skill code-review
```

### 3. Diretamente no Chat
```
Qualquer conversa com Claude Code pode usar:
/code-review
/dataviz
/simplify
/loop
/claude-api
```

---

## 📚 DOCUMENTAÇÃO OFICIAL

- **Claude Code:** https://claude.ai/code
- **Skills:** Disponíveis nativamente no Claude Code
- **API Docs:** https://claude.ai/docs

---

## ✅ CHECKLIST: SKILLS SETUP

- [ ] Acesso ao Claude Code confirmado
- [ ] `/code-review` testado (rode em diff simples)
- [ ] `/dataviz` testado (rode em design mockup)
- [ ] `/simplify` testado (rode em código duplicado)
- [ ] `/loop` entendido (para Fase 0 validation)
- [ ] Equipe estudou essa documentação

---

## 💡 DICAS PRÁTICAS

### Dica 1: /code-review é iterativo
```
Primeira rodada: /code-review low (encontra problemas óbvios)
Segunda rodada: /code-review medium (refine)
Terceira rodada: /code-review high (análise completa)
```

### Dica 2: /dataviz cria baseline
```
/dataviz
  ↓
Gera: palette.md com cores validadas
Gera: Recomendações de chart types
Gera: Accessibility checklist
Você implementa com essa base
```

### Dica 3: /simplify é seguro
```
Não apaga código, só propõe refactors
Você revisa antes de aceitar
Ótimo para antes de escrever código novo
```

### Dica 4: /loop monitora Fase 0
```
/loop 5m (por 1 hora)
Detecta se workflow parou de rodar
Valida que JSON tá sendo gerado
Se parar, você vê o erro imediatamente
```

---

## 🚀 PRÓXIMO PASSO

1. **Abra Claude Code**
2. **Digite:** `/code-review`
3. **Teste em qualquer PR ou diff**
4. **Vire profissional rapidinho!** 🎯

---

**Todas as skills estão prontas. Pode começar Fase 0 agora mesmo! 🚀**
