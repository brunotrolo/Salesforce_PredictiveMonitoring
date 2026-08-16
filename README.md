# Salesforce Predictive Monitoring

Sistema de monitoramento preditivo para logs do Salesforce usando heurística e machine learning.

**Status:** ✅ Phase 0 Ready for Execution  
**Timeline:** 4-5 semanas (Phases 0-5)  
**Cost:** $0/mês  
**Tech Stack:** Python 3.10+, Node 18+, GitHub Actions, MCP Salesforce

---

## 📖 LEITURA OBRIGATÓRIA (Ordem)

### 1️⃣ SPECIFICATION.md (10 min)
**Spec-Driven Development consolidada com todos os requisitos e testes.**

```bash
# Validar que tudo está pronto
git log --oneline -10
```

### 2️⃣ PROJECT_ROADMAP_MASTER.md (15 min)
**Roadmap 4-5 semanas com phases 0-5, recursos e timeline.**

### 3️⃣ docs/ARCHITECTURE_DECISIONS.md (30 min)
**10 ADRs explicando decisões arquiteturais do projeto.**

### 4️⃣ Role-Specific Guides

**Backend Engineer:**
- `docs/FASE_0_IMPLEMENTATION_GUIDE.md` (Seções 2-3)

**Frontend Engineer:**
- `docs/FASE_0_IMPLEMENTATION_GUIDE.md` (Seção 2, frontend part)

**DevOps/SRE:**
- `docs/FASE_0_IMPLEMENTATION_GUIDE.md` (Seção 1)

### 5️⃣ docs/PHASE_0_QUICK_REFERENCE.md
**Imprima este arquivo e coloque na mesa durante Phase 0.**

---

## 🎯 ESTRUTURA DO PROJETO

```
├── README.md (este arquivo)
├── SPECIFICATION.md ⭐ (SDD master - COMECE AQUI)
├── PROJECT_ROADMAP_MASTER.md (Roadmap 4-5 semanas)
└── docs/
    ├── ARCHITECTURE_DECISIONS.md (10 ADRs)
    ├── CLAUDE_CODE_SKILLS.md (5 native platform skills)
    ├── GITHUB_PROJECT_REFERENCES.md (18 dependencies)
    ├── FASE_0_IMPLEMENTATION_GUIDE.md (Step-by-step Phase 0)
    └── PHASE_0_QUICK_REFERENCE.md (Daily checklist)
```

---

## 🚀 PHASE 0 QUICK START

### Setup (5 min)
```bash
git clone https://github.com/brunotrolo/Salesforce_PredictiveMonitoring.git
cd Salesforce_PredictiveMonitoring
git checkout main
```

### Verificar pré-requisitos
```bash
python --version  # Esperado: ≥3.10
node --version    # Esperado: ≥18
git --version     # Configurado com credentials
```

### Ler a spec (45 min)
```bash
# Abrir SPECIFICATION.md e ler seções 1-4
cat SPECIFICATION.md | head -200
```

### Começar Phase 0 (Dia 1)
```bash
# Seguir docs/PHASE_0_QUICK_REFERENCE.md
cat docs/PHASE_0_QUICK_REFERENCE.md
```

---

## 📚 DOCUMENTAÇÃO ESSENCIAL

| Documento | Propósito | Tempo |
|---|---|---|
| **SPECIFICATION.md** | SDD consolidada com testes | 10 min |
| **PROJECT_ROADMAP_MASTER.md** | Timeline + phases 0-5 | 15 min |
| **docs/ARCHITECTURE_DECISIONS.md** | 10 decisões arquiteturais | 30 min |
| **docs/CLAUDE_CODE_SKILLS.md** | Guide: /code-review, /dataviz, etc | 20 min |
| **docs/GITHUB_PROJECT_REFERENCES.md** | 18 dependências + fases | 15 min |
| **docs/FASE_0_IMPLEMENTATION_GUIDE.md** | Step-by-step Phase 0 | 40 min |
| **docs/PHASE_0_QUICK_REFERENCE.md** | Daily checklist (IMPRIMA) | 5 min |

**Total reading time:** ~2 horas (faça antes do kickoff)

---

## ⚡ KEY CONCEPTS

### Claude Code Skills (Nativo)
Recursos da plataforma acessados via `/comando`:
- `/code-review` - Revisão de código
- `/dataviz` - Design de visualizações
- `/simplify` - Refatoração
- `/loop` - Monitoramento contínuo
- `/claude-api` - Referência API

**Acesso:** https://claude.ai/code

### GitHub Project References (Externo)
Dependências instaladas via pip/npm:
- **Phase 0:** Pydantic, structlog, pytest, faker, Jest, Tailwind CSS, etc (11 projetos)
- **Phase 1:** pandas, factory_boy, Storybook (3 projetos)
- **Phase 5+:** Sentry, Prometheus (2 projetos)

**Total:** 18 projetos documentados

---

## 📊 PROJECT METRICS

| Métrica | Valor |
|---|---|
| **Documentação** | 4,125 linhas (8 arquivos) |
| **ADRs** | 10 (todas ACCEPTED) |
| **Phases** | 6 (0-5) |
| **Timeline** | 4-5 semanas |
| **Team Size** | 3 (Backend, Frontend, DevOps) |
| **Cost** | $0/mês |
| **Coverage Target** | Backend 80%, Frontend 70% |

---

## ✅ ANTES DE COMEÇAR PHASE 0

- [ ] Equipe leu SPECIFICATION.md
- [ ] Equipe leu PROJECT_ROADMAP_MASTER.md
- [ ] Roles atribuídos (Backend, Frontend, DevOps)
- [ ] Python 3.10+ instalado
- [ ] Node 18+ instalado
- [ ] Git configurado
- [ ] Repo clonado
- [ ] Branch sincronizado

---

## 🔗 LINKS IMPORTANTES

- **Repository:** https://github.com/brunotrolo/Salesforce_PredictiveMonitoring
- **Claude Code:** https://claude.ai/code
- **Claude API:** https://claude.ai/docs

---

## 📞 ESCALATION

**Dúvidas sobre:**
- **Arquitetura:** Veja `docs/ARCHITECTURE_DECISIONS.md`
- **Timeline:** Veja `PROJECT_ROADMAP_MASTER.md`
- **Implementação:** Veja `docs/FASE_0_IMPLEMENTATION_GUIDE.md`
- **Daily:** Use `docs/PHASE_0_QUICK_REFERENCE.md`

---

## 📈 PROJECT STATUS

```
✅ Phase 0 Planning & Validation: COMPLETE
✅ Architecture Decision Records: 10 (all ACCEPTED)
✅ Documentation: 8 files (4,125 lines)
✅ Spec-Driven Development: READY
✅ Team onboarding: READY
✅ Technical validation: PASSED

🚀 READY FOR PHASE 0 EXECUTION
```

---

**Última atualização:** 2026-08-15  
**Versão:** 1.0 (SDD Ready)  
**Próximo:** Ler SPECIFICATION.md e começar Phase 0
