# LINKS DAS SKILLS - ACESSO DIRETO

**Data:** 2026-08-15  
**Projeto:** Salesforce Predictive Monitoring

---

## 🔗 LINKS DIRETOS PARA SKILLS

### As skills do Claude Code não têm URLs públicas no GitHub
As skills são **recursos nativos da plataforma Claude Code** e são acessadas via slash commands dentro da interface, não via URLs.

---

## 📍 COMO ACESSAR CADA SKILL

### 1. `/code-review`
**Link de Acesso:**
- https://claude.ai/code (web)
- Claude Code Desktop (offline)

**Como usar:**
```
1. Abra https://claude.ai/code
2. Faça um commit com código que quer revisar
3. Digite: /code-review
4. Escolha: low, medium, ou high
5. Claude revisa seu código
```

**Uso no Projeto:**
- Toda PR de Python (services/)
- Antes de merge em main
- `/code-review medium --comment` para comentários inline

---

### 2. `/dataviz`
**Link de Acesso:**
- https://claude.ai/code (web)
- Claude Code Desktop (offline)

**Como usar:**
```
1. Abra https://claude.ai/code
2. Descreva o dashboard que quer desenhar
3. Digite: /dataviz
4. Claude fornece:
   - Paleta de cores validada
   - Chart recommendations
   - Layout/responsividade
   - Accessibility checklist
```

**Uso no Projeto:**
- Fase 0: Design monitoring dashboard (1x)
- Descrever: risk gauge, line chart, alerts, health banner
- Resultado: `references/palette.md` + Tailwind classes

---

### 3. `/simplify`
**Link de Acesso:**
- https://claude.ai/code (web)
- Claude Code Desktop (offline)

**Como usar:**
```
1. Faça um commit com código repetitivo
2. Abra https://claude.ai/code
3. Digite: /simplify
4. Claude refatora eliminando duplicação
```

**Uso no Projeto:**
- Antes de escrever novo código
- Limpeza de heuristic.py (Fase 1)
- Refactor de comparison logic (Fase 3)

---

### 4. `/loop`
**Link de Acesso:**
- https://claude.ai/code (web)
- Claude Code Desktop (offline)

**Como usar:**
```
1. Abra https://claude.ai/code
2. Digite: /loop 5m
3. Descreva o comando a executar
4. Claude executa a cada 5 minutos
5. Para: /loop stop
```

**Uso no Projeto:**
- Fase 0: Validar workflow roda continuamente
- Exemplo: `/loop 5m` verifica se Git tem novo commit a cada 5 min
- Duração: por 1 hora (validação)

---

### 5. `/claude-api` (opcional, Fase 5+)
**Link de Acesso:**
- https://claude.ai/code (web)
- Claude Code Desktop (offline)

**Como usar:**
```
1. Abra https://claude.ai/code
2. Digite: /claude-api
3. Faça perguntas sobre Claude API
4. Claude fornece: models, pricing, features, SDKs
```

**Uso no Projeto:**
- Apenas se usar LLM em Fase 5+
- Exemplo: Claude analisa logs anômalos
- Não aplicável agora (Fase 0-4)

---

## 📚 DOCUMENTAÇÃO NO REPOSITÓRIO

### Links para Documentos do Projeto

**Arquivo:** https://github.com/brunotrolo/Salesforce_PredictiveMonitoring/blob/main/SKILLS_LINKS.md
- Guia completo de como usar cada skill
- Exemplos práticos
- Checklist por fase
- Dicas e truques

**Arquivo:** https://github.com/brunotrolo/Salesforce_PredictiveMonitoring/blob/main/SKILLS_E_TOOLING.md
- Skills profissionais por componente
- Timing de uso em cada fase
- Ferramentas adicionais recomendadas
- Checklist de qualidade

**Arquivo:** https://github.com/brunotrolo/Salesforce_PredictiveMonitoring/blob/main/STATUS_VALIDACAO_FINAL.md
- Skills por fase
- Quando usar cada uma
- Próximos passos

---

## 🚀 ACESSO RÁPIDO

### Abra Claude Code Agora
```
https://claude.ai/code
```

### Comandos Rápidos
```
/code-review              → Revisar código
/dataviz                  → Design dashboard
/simplify                 → Refatorar
/loop 5m /seu-comando     → Executar repetidamente
/claude-api               → Referência API Claude
```

---

## 📋 CHECKLIST: PRIMEIRA EXECUÇÃO

```
[ ] Abrir https://claude.ai/code
[ ] Digitar: /code-review
[ ] Escolher um diff para revisar
[ ] Ver Claude revisar o código
[ ] Aplicar sugestões
[ ] Repetir com /simplify se necessário
[ ] Done! Código profissional! ✨
```

---

## 🔍 INTEGRAÇÃO COM GITHUB

### Fluxo Típico
```
1. Você escreve código em services/heuristic/
2. git add + git commit
3. git push para branch feature
4. Abre PR em GitHub
5. Abre Claude Code: https://claude.ai/code
6. Digita: /code-review medium --comment
7. Claude posta comentários inline na PR
8. Você corrige os issues
9. Merge na main
```

---

## 💡 ATALHOS ÚTEIS

### Web
- Tecla: `/` (slash) para invocar skills
- Tab para autocomplete

### Desktop
- Mesma interface que web
- Funciona offline
- Atalho: cmd+k (Mac) ou ctrl+k (Windows/Linux)

---

## ❓ FAQ

**P: Posso usar skills sem internet?**  
R: Sim, com Claude Code Desktop (offline).

**P: As skills têm custo adicional?**  
R: Não, estão incluídas na subscrita Claude Code.

**P: Preciso de conta GitHub?**  
R: Sim, para integração com repositórios. Já tem! ✓

**P: Posso usar skills em qualquer IDE?**  
R: Não, apenas em Claude Code (web ou desktop).

**P: E se a skill não funcionar?**  
R: Tente digitar `/` novamente, ou reinicie Claude Code.

---

## 🎯 PRÓXIMO: COMEÇAR FASE 0

1. ✅ Abrir: https://claude.ai/code
2. ✅ Testar: `/code-review` em um diff simples
3. ✅ Testar: `/dataviz` descrevendo um componente
4. ✅ Confirmar: Tudo funciona
5. ✅ Começar: Fase 0 do projeto

---

**Tudo pronto. Skills disponíveis. Comece agora! 🚀**

**Links principais:**
- Claude Code: https://claude.ai/code
- Seu Repositório: https://github.com/brunotrolo/Salesforce_PredictiveMonitoring
- Documentação: https://github.com/brunotrolo/Salesforce_PredictiveMonitoring/blob/main/SKILLS_LINKS.md
