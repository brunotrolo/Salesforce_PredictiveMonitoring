# CLAUDE CODE SKILLS - GUIA DE USO
**Projeto:** Salesforce Predictive Monitoring  
**Data:** 2026-08-15  
**Plataforma:** Claude Code

---

## 📌 O QUE SÃO SKILLS DO CLAUDE CODE?

Skills são **recursos nativos da plataforma Claude Code** acessados via **slash commands** (`/comando`). Não são URLs públicas no GitHub - são ferramentas integradas no Claude Code web/desktop.

---

## 🎯 SKILLS RECOMENDADAS PARA O PROJETO

### 1. `/code-review` ⭐ CRÍTICA

**O que faz:**  
Revisa código para bugs, performance, test coverage, simplificações.

**Como usar:**
```
/code-review                    # Revisa diff atual (low effort)
/code-review medium             # Esforço médio (balanceado)
/code-review high               # Esforço alto (análise completa)
/code-review --comment          # Posta findings como comentários inline na PR
```

**Quando usar no projeto:**
- ✅ **Fase 0:** Toda PR de Python (services/)
- ✅ **Fase 1:** Validar integração MCP
- ✅ **Fase 3:** HIGH effort para services/comparison/ (Prophet + Isolation Forest)
- ✅ **Todas as fases:** Toda PR de backend

**Exemplo prático Fase 0:**
```bash
# Terminal - fazer commit com novo código
git checkout -b feature/heuristic-v2
# ... escreve services/heuristic/src/heuristic.py ...
git add services/heuristic/src/heuristic.py
git commit -m "feat: implement heuristic risk score calculation"

# No Claude Code:
/code-review medium --comment
# Resultado: Claude posta findings inline na PR, você aplica sugestões
```

**Benefício para o projeto:**
- Catch bugs antes de merge
- Validar coverage ≥80%
- Code style consistency
- Performance suggestions

**Acesso:** https://claude.ai/code

---

### 2. `/dataviz` ⭐ CRÍTICA PARA FRONTEND

**O que faz:**  
Design de visualizações (cores, charts, acessibilidade, responsividade).

**Como usar:**
```
/dataviz
(Descreva o componente que quer desenhar)
```

**Quando usar no projeto:**
- ✅ **Fase 0:** 1x (design do monitoring dashboard)
  - Risk score gauge (0-1, circular)
  - Line chart (histórico 30 dias)
  - Alerts panel (severity badges)
  - Health check banner

**Exemplo prático Fase 0:**
```
Você (no Claude Code):
  "Preciso de um dashboard com:
   - Gauge circular para risk_score (0-1)
   - Cores: verde (0-0.3), amarelo (0.3-0.7), vermelho (0.7-1)
   - Line chart com 30 dias de histórico
   - Alert badges: CRÍTICA=red, ALTA=orange, MÉDIA=yellow
   - Responsivo: mobile (375px), tablet (768px), desktop (1920px)
   - Dark mode support"

Claude (via /dataviz):
  ✓ Paleta de cores validada (light/dark)
  ✓ Chart recommendations (Chart.js vs D3 vs Recharts)
  ✓ Layout grid + breakpoints (Tailwind)
  ✓ Accessibility checklist (WCAG 2.1 AA)
  ✓ Contrast ratios validados
  ✓ Mobile-first approach
```

**Benefício para o projeto:**
- Design profissional sem designer
- Acessibilidade garantida
- Dark mode automático
- Responsividade validada

**Acesso:** https://claude.ai/code

---

### 3. `/simplify` ⭐ IMPORTANTE

**O que faz:**  
Refactora código para eliminar duplicação, simplificar logic, melhorar eficiência.

**Como usar:**
```
/simplify
(Executa no diff atual - mostra refactorings propostos)
```

**Quando usar no projeto:**
- ✅ **Fase 0:** Antes de escrever services/heuristic/src/heuristic.py
- ✅ **Fase 1:** Limpeza geral de transformação Pandas
- ✅ **Fase 3:** Antes de services/comparison/ (ML logic pode ficar complexa)
- ✅ **Fase 4:** Cleanup de weekly_retrain.py

**Exemplo prático Fase 1:**
```python
# Antes (repetitivo em services/heuristic/):
def analyze(logs):
    errors = []
    for log in logs:
        if log['status_code'] >= 500:
            errors.append(log)
    
    slow = []
    for log in logs:
        if log['duration_ms'] > 1000:
            slow.append(log)
    
    critical = []
    for log in logs:
        if log['status_code'] >= 500 and log['duration_ms'] > 1000:
            critical.append(log)

# No Claude Code:
/simplify

# Resultado Claude propõe:
def analyze(logs):
    errors = [l for l in logs if l['status_code'] >= 500]
    slow = [l for l in logs if l['duration_ms'] > 1000]
    critical = [l for l in logs if l['status_code'] >= 500 and l['duration_ms'] > 1000]
```

**Benefício para o projeto:**
- DRY principle (Don't Repeat Yourself)
- Readability melhorada
- Performance potencial
- Menos bugs

**Acesso:** https://claude.ai/code

---

### 4. `/loop` (Monitoramento)

**O que faz:**  
Executa um comando/prompt repetidamente em intervalo.

**Como usar:**
```
/loop 5m /seu-comando-aqui
/loop 10m /seu-prompt-aqui
/loop stop
```

**Quando usar no projeto:**
- ⚠️ **Fase 0 APENAS:** Para validar que workflow roda continuamente

**Exemplo prático Fase 0:**
```
/loop 5m
Verifique se o último workflow `monitoring-collect.yml` rodou com sucesso
nos últimos 5 minutos, validando:
- Coleta de dados mock completa
- JSON output foi gerado
- Arquivo contém risk_score válido (0-1)
```

**Duração:** 1 hora (validação inicial)

**Benefício para o projeto:**
- Detectar se workflow parou
- Validar dados sendo gerados
- Identificar erros rapidinho

**Acesso:** https://claude.ai/code

---

### 5. `/claude-api` (Opcional, Fase 5+)

**O que faz:**  
Referência de Claude API (models, pricing, features, SDKs).

**Como usar:**
```
/claude-api
(Descreva o que quer fazer com Claude API)
```

**Quando usar no projeto:**
- ⚠️ **Fase 5 APENAS:** Se decidir usar Claude para análise inteligente
  - Exemplo: LLM analisa logs anômalos e sugere causa raiz
  - Exemplo: Claude refina thresholds da heurística baseado em histórico

**Não aplicável agora (Fase 0-4).**

**Acesso:** https://claude.ai/code

---

## 📊 SKILLS POR FASE - QUANDO USAR

### Fase 0 (Scaffold + Mocks)
```
/code-review low              ← Validar estrutura inicial
/dataviz                      ← Design dashboard mockup (1x)
/loop 5m                      ← Monitor workflow continuidade (1 hora)
```

### Fase 1 (Coleta Real + Heurística)
```
/code-review medium           ← PR de collector + heuristic
/dataviz (refinement)         ← Ajustar dashboard com dados reais
/simplify                     ← Limpar heuristic.py se necessário
```

### Fase 2 (Alertas + Notificações)
```
/code-review medium           ← Notification logic
/dataviz                      ← Severity colors no dashboard
```

### Fase 3 (Modo Sombra ML)
```
/code-review high             ← Prophet + Isolation Forest
/simplify                     ← Refactor comparison logic
```

### Fase 4 (Feedback Loop)
```
/code-review medium           ← Retrain logic
/dataviz (refinement)         ← Feedback UX
```

### Fase 5 (Hardening)
```
/code-review high             ← Error handling + retry
/simplify                     ← Cleanup geral
/claude-api (opcional)        ← Se usar LLM em produção
```

---

## 🎯 COMO ACESSAR SKILLS DO CLAUDE CODE

### Via Web
1. Abra https://claude.ai/code
2. Digite `/` (slash) para ver skills disponíveis
3. Digite `/code-review` (ou outra skill)
4. Pressione Tab ou Enter

### Via Desktop
- Claude Code Desktop (offline também)
- Mesmos comandos `/` 
- Atalho: cmd+k (Mac) ou ctrl+k (Windows/Linux)

### Autocomplete
- Pressione `/` e espere sugestões
- Use Tab para navegar
- Enter para selecionar

---

## 💡 DICAS DE USO

### Dica 1: /code-review é Iterativo
```
Primeira rodada: /code-review low      (encontra problemas óbvios)
Segunda rodada:  /code-review medium   (refine)
Terceira rodada: /code-review high     (análise completa)
```

### Dica 2: /dataviz Cria Baseline
```
/dataviz
  ↓ Gera: palette.md com cores validadas
  ↓ Gera: Recomendações de chart types
  ↓ Gera: Accessibility checklist
  ↓ Você implementa com essa base (em site/monitoring/)
```

### Dica 3: /simplify é Seguro
```
Não apaga código - só propõe refactors
Você revisa antes de aceitar
Ótimo para antes de escrever código novo
```

### Dica 4: /loop Monitora Fase 0
```
/loop 5m (por 1 hora)
  ↓ Detecta se workflow parou
  ↓ Valida que JSON tá sendo gerado
  ↓ Se parar, você vê o erro imediatamente
```

---

## ✅ CHECKLIST: SKILLS SETUP

- [ ] Acesso ao Claude Code confirmado (https://claude.ai/code)
- [ ] `/code-review` testado (rode em diff simples)
- [ ] `/dataviz` testado (rode em design mockup)
- [ ] `/simplify` testado (rode em código duplicado)
- [ ] `/loop` entendido (para Fase 0 validation)
- [ ] Equipe estudou esta documentação

---

## 🔗 LINKS IMPORTANTES

- **Claude Code Web:** https://claude.ai/code
- **Claude Code Desktop:** Baixar em claude.ai
- **Claude API Docs:** https://claude.ai/docs (se usar /claude-api)
- **Seu Repositório:** https://github.com/brunotrolo/Salesforce_PredictiveMonitoring

---

## ❓ FAQ - SKILLS DO CLAUDE CODE

**P: Posso usar skills sem internet?**  
R: Sim, com Claude Code Desktop (offline). Skills rodam na máquina local.

**P: As skills têm custo adicional?**  
R: Não, estão incluídas na subscrição Claude Code.

**P: Preciso de conta GitHub?**  
R: Sim, para integração com repositórios (já tem!).

**P: Posso usar skills em qualquer IDE?**  
R: Não, apenas em Claude Code (web ou desktop).

**P: E se a skill não funcionar?**  
R: Tente digitar `/` novamente, ou reinicie Claude Code.

**P: Qual skill uso para testes?**  
R: `/code-review high` foca em test coverage.

**P: Qual skill uso para design?**  
R: `/dataviz` para visualizações.

**P: Posso rodar /loop 24/7?**  
R: Sim, mas use para validações (Fase 0). Depois use CI/CD real (GitHub Actions).

---

## 🚀 PRÓXIMO: COMEÇAR FASE 0

1. ✅ Abrir: https://claude.ai/code
2. ✅ Testar: `/code-review` em um diff simples
3. ✅ Testar: `/dataviz` descrevendo um componente
4. ✅ Confirmar: Tudo funciona
5. ✅ Começar: Fase 0 seguindo docs/FASE_0_IMPLEMENTATION_GUIDE.md

---

**Skills do Claude Code estão prontas para usar!**

Durante Fase 0, use `/code-review` em cada PR e `/dataviz` uma vez para o dashboard.

Dúvidas? Acesse https://claude.ai/code ou crie issue no repositório.
