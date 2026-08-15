# PLANO: MONITORAMENTO PREDITIVO SALESFORCE (Nebula Logger + ML)
## Arquitetura v2: 100% GitHub (Actions + Pages + Issues)

**Status:** Plano Aprovado - Pronto para Implementação
**Data:** 2026-08-15
**Repositório:** brunotrolo/brunotrolo
**Role:** AI Solution Architect

---

## CONTEXTO E MOTIVO DA MUDANÇA DE ARQUITETURA

A primeira versão deste plano usava Apps Script + Google Colab + Google Sheets. Na prática, essa arquitetura tinha um problema estrutural: o Colab (gratuito) só fica confiavelmente ativo com uma aba do navegador aberta — "background execution" sem aba aberta é recurso do Colab Pro (pago). Isso contradiz diretamente o requisito original: **rodar 24/7 sem depender de alguém manter um navegador aberto**.

A nova arquitetura resolve isso movendo tudo para o GitHub:

- **GitHub Actions** substitui o Apps Script como orquestrador — roda em `schedule` (cron), 100% headless, sem navegador, sem sessão que expira
- **Python real dentro do runner do GitHub Actions** substitui o Colab — Prophet e Isolation Forest rodam no mesmo job que coleta os dados, sem precisar de um segundo salto (nada de ngrok, nada de URL efêmera)
- **Arquivos JSON versionados no repositório** substituem o Google Sheets como camada de dados
- **GitHub Pages** substitui o Web App do Apps Script como front-end
- **GitHub Issues** substitui a necessidade de um backend de escrita — é o único ponto onde um humano precisa "gravar" algo (feedback de falso positivo), e isso é resolvido com um link pré-preenchido para abrir uma Issue, sem token exposto e sem servidor próprio

**Resultado:** zero dependência de navegador aberto, zero infraestrutura fora do GitHub e do Salesforce.

### Decisão adicional: heurística adaptativa primeiro, ML em modo sombra depois

Prophet e Isolation Forest precisam de semanas de histórico pra ajustar bem (problema de "cold start") — nas primeiras semanas deste projeto, sem esse histórico, eles podem performar pior que uma heurística simples bem calibrada. Por isso a Fase 1 usa uma **heurística adaptativa** (média móvel por padrão de horário + desvio, sem dependências de ML) como modelo principal, e Prophet/Isolation Forest entram só na Fase 3, rodando em **modo sombra** (registrando previsões, sem disparar alerta sozinhos) até haver dado real suficiente para provar, por comparação direta, se valem a complexidade extra.

---

## ARQUITETURA

```
Salesforce (Nebula Logger)
    ↓ (GitHub Actions, cron a cada 5 min, runner com Python)
    ├─ Autentica via OAuth refresh_token (credenciais em GitHub Secrets)
    ├─ Consulta últimos 30 min de logs via REST API
    ├─ Heurística adaptativa (principal, dispara alerta) — Fase 1
    ├─ Prophet + Isolation Forest (modo sombra, só registra) — Fase 3+
    └─ Gera JSON: snapshot atual + histórico + alertas + registro comparativo
         ↓
    Commit automático no branch `data` (isolado do branch de código)
         ↓
GitHub Pages (site estático: HTML/CSS/JS, deploy raro — só quando o site muda)
    ↓ (JS do front-end busca os JSONs direto do branch `data` via raw.githubusercontent.com)
    ↓ (auto-refresh client-side a cada 5 min, sem precisar redeploy do site)
Dashboard: risco atual, previsão, histórico, botão de feedback
    ↓ (clique em "Marcar como Falso Positivo")
GitHub Issues (link pré-preenchido, usuário já logado no GitHub confirma o envio)
    ↓ (Action disparada por `issues: opened` com label `feedback`)
Atualiza feedback.json → ajusta threshold da heurística e retreina o modelo sombra
```

### Por que separar branch de código (`master`) e branch de dados (`data`)

O workflow escrito em `master` roda o script Python e o resultado é commitado num branch `data` dedicado. Isso evita poluir o histórico de commits do código com centenas de commits de dados por dia (a cada 5 min = ~288 commits/dia). O branch `data` cresce rápido, mas isso é esperado e não afeta PRs, releases ou histórico do código-fonte.

**Detalhe técnico importante:** o GitHub só dispara o gatilho `schedule` (cron) para arquivos de workflow que estão no branch padrão (`master`). Por isso o `.yml` do workflow mora em `master`, mas o script, ao final da execução, troca para o branch `data` só para gravar o resultado.

### Por que o front-end busca dados direto do branch `data` (sem redeploy do Pages)

O site publicado no GitHub Pages (HTML/CSS/JS) quase não muda — só quando alteramos a interface. Os *dados*, sim, mudam a cada 5 minutos. Separando as duas coisas, o JavaScript do dashboard busca o JSON mais recente direto via `https://raw.githubusercontent.com/brunotrolo/brunotrolo/data/monitoring/latest.json`, sem precisar de um novo deploy do Pages a cada atualização. Isso é possível porque `brunotrolo/brunotrolo` é um repositório público — conteúdo raw é acessível publicamente sem autenticação.

---

## ESTRUTURA DE ARQUIVOS

```
monitoring/
├── scripts/
│   ├── collect_and_predict.py    (autentica, consulta Nebula Logger, roda a heurística — Fase 1)
│   ├── heuristic.py              (EWMA por bucket de horário + z-score/MAD + threshold ajustável)
│   ├── shadow_ml.py              (Prophet + Isolation Forest em modo sombra — só a partir da Fase 3)
│   ├── compare_models.py         (calcula precisão recente de cada abordagem no registro comparativo)
│   ├── process_feedback.py       (lê o corpo de uma Issue de feedback, atualiza feedback.json)
│   ├── weekly_retrain.py         (ajusta thresholds da heurística e retreina o modelo sombra — Fase 4)
│   └── requirements.txt          (Fase 1: pandas, requests — sem prophet/scikit-learn ainda)
├── site/                          (fonte do GitHub Pages)
│   ├── index.html
│   ├── styles.css
│   └── app.js                     (fetch dos JSONs, auto-refresh, gráficos, botão de feedback)
└── data/                          (só existe no branch `data`, não em `master`)
    ├── latest.json                (snapshot atual: risk_score da heurística, timestamp)
    ├── history.json               (janela de 30 dias, usada nos gráficos de tendência)
    ├── alerts.json                (lista de alertas/problemas detectados)
    ├── predictions.json           (registro comparativo: heurística vs. modelo sombra vs. resultado real — Fase 3+)
    └── feedback.json              (registros de falso positivo, usados no ajuste/retreino)

.github/workflows/
├── monitoring-collect.yml         (cron */5 * * * *, coleta + heurística [+ sombra na Fase 3+] + commit no branch data)
├── monitoring-feedback.yml        (on: issues opened com label 'feedback', processa e commita)
├── monitoring-retrain.yml         (cron semanal, ajusta thresholds e retreina o modelo sombra — Fase 4+)
└── monitoring-tests.yml           (roda pytest a cada push/PR em monitoring/**)
```

---

## SOQL DE COLETA (Nebula Logger)

```sql
SELECT Id, Message__c, ServiceDuration__c, StatusCode__c, CreatedDate
FROM Log__c
WHERE CreatedDate = LAST_N_MINUTES:30
ORDER BY CreatedDate DESC
LIMIT 500
```

Autenticação: OAuth 2.0 `refresh_token` grant contra `https://login.salesforce.com/services/oauth2/token`, mesmas credenciais do Connected App já documentado em `SALESFORCE_MCP_SETUP.md`, agora armazenadas como **GitHub Secrets** (`SF_CLIENT_ID`, `SF_CLIENT_SECRET`, `SF_REFRESH_TOKEN`) em vez de Script Properties do Apps Script.

**Nota sobre "MCP":** como já esclarecido na versão anterior deste plano, o MCP Salesforce é feito para ser consumido por agentes de IA (Claude), não por scripts. O workflow do GitHub Actions replica o mesmo fluxo OAuth + REST que o MCP usa por baixo dos panos, em Python puro (`requests`), sem a camada MCP.

---

## EXEMPLO DE WORKFLOW (coleta + predição)

```yaml
name: Coleta e Predição - Nebula Logger
on:
  schedule:
    - cron: '*/5 * * * *'
  workflow_dispatch:

jobs:
  collect-predict:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r monitoring/scripts/requirements.txt
      - run: python monitoring/scripts/collect_and_predict.py --output-dir /tmp/data-output
        env:
          SF_CLIENT_ID: ${{ secrets.SF_CLIENT_ID }}
          SF_CLIENT_SECRET: ${{ secrets.SF_CLIENT_SECRET }}
          SF_REFRESH_TOKEN: ${{ secrets.SF_REFRESH_TOKEN }}
      - name: Publica no branch data
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git fetch origin data
          git checkout data
          mkdir -p monitoring/data
          cp -r /tmp/data-output/* monitoring/data/
          git add monitoring/data/
          git commit -m "Atualiza dados de monitoramento $(date -u +%Y-%m-%dT%H:%M:%SZ)" || echo "Sem mudanças"
          git push origin data
```

**Permissão necessária:** o token padrão do GitHub Actions (`GITHUB_TOKEN`) precisa de `permissions: contents: write` no workflow para conseguir commitar — mesmo padrão já usado no `snake.yml` existente neste repositório.

---

## FRONT-END (GitHub Pages)

```javascript
// monitoring/site/app.js
const DATA_BASE = 'https://raw.githubusercontent.com/brunotrolo/brunotrolo/data/monitoring/data';

async function fetchLatest() {
  const res = await fetch(`${DATA_BASE}/latest.json?t=${Date.now()}`); // evita cache
  return res.json();
}

function renderDashboard(data) {
  document.getElementById('risk-score').textContent = data.risk_score.toFixed(2);
  document.getElementById('last-updated').textContent = data.timestamp;
  // health check simplificado: dado desatualizado?
  const ageMinutes = (Date.now() - new Date(data.timestamp)) / 60000;
  document.getElementById('health-banner').style.display = ageMinutes > 15 ? 'block' : 'none';
}

async function refresh() {
  renderDashboard(await fetchLatest());
}
setInterval(refresh, 5 * 60 * 1000);
refresh();
```

**Botão de feedback (marca falso positivo via GitHub Issues, sem backend próprio):**
```html
<a id="feedback-link" href="#" target="_blank">Marcar como Falso Positivo</a>
<script>
function buildFeedbackLink(alertId) {
  const title = encodeURIComponent(`Feedback: Falso Positivo (${alertId})`);
  const body = encodeURIComponent(`alert_id: ${alertId}\ntimestamp: ${new Date().toISOString()}`);
  return `https://github.com/brunotrolo/brunotrolo/issues/new?title=${title}&labels=feedback&body=${body}`;
}
</script>
```

O usuário clica, o GitHub abre a página nativa de criar Issue já preenchida, ele confirma com a própria conta do GitHub — sem exposição de token, sem servidor de escrita próprio.

---

## PROCESSAMENTO DO FEEDBACK (Issues → dados)

```yaml
name: Processa Feedback de Monitoramento
on:
  issues:
    types: [opened]

permissions:
  contents: write
  issues: write

jobs:
  process-feedback:
    if: contains(github.event.issue.labels.*.name, 'feedback')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: python monitoring/scripts/process_feedback.py
        env:
          ISSUE_BODY: ${{ github.event.issue.body }}
          ISSUE_NUMBER: ${{ github.event.issue.number }}
      - name: Commita no branch data e fecha a Issue
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git fetch origin data && git checkout data
          git add monitoring/data/feedback.json
          git commit -m "Feedback registrado via Issue #${{ github.event.issue.number }}"
          git push origin data
      - run: gh issue close ${{ github.event.issue.number }} --comment "Feedback registrado, obrigado!"
        env: { GH_TOKEN: ${{ secrets.GITHUB_TOKEN }} }
```

---

## FASES

### Fase 0 — Validação de Conectividade (reduzida)

Com essa arquitetura, o número de elos externos cai de 2 (Salesforce + Colab) para 1 (só Salesforce) — o ML já roda dentro do próprio runner, então não existe mais "o Colab não acordou". A validação fica mais simples:

**Definition of Done:**
- [ ] Workflow do GitHub Actions autentica no Salesforce (via Secrets) e executa 1 SOQL trivial com sucesso
- [ ] Workflow consegue commitar um JSON de teste no branch `data` (valida `permissions: contents: write`)
- [ ] GitHub Pages está habilitado e serve o site estático publicamente
- [ ] Página de teste consegue buscar o JSON via `raw.githubusercontent.com` e exibir na tela
- [ ] Workflow roda no cron (`*/5 * * * *`) por pelo menos 1 hora sem falha
- [ ] Testes unitários (pytest) rodam no CI antes de qualquer merge

**Riscos específicos:**

| Risco | Mitigação |
|-------|-----------|
| Salesforce Trusted IP Range rejeita os IPs dos runners do GitHub (dinâmicos/compartilhados) | Relaxar IP restriction no Connected App, ou allowlist dos ranges de IP publicados pelo GitHub |
| Cron do GitHub Actions atrasa em picos de carga (documentado pelo próprio GitHub) | Tratar 5 min como alvo, não garantia rígida; monitorar horário real das execuções no histórico de Actions |
| Repositório precisa ser público para Pages gratuito + Actions com minutos ilimitados | Confirmar visibilidade do repositório antes de iniciar |
| `refresh_token` expira ou é revogado | Documentar processo de renovação manual no runbook |

---

### Fase 1 — MVP com Heurística Adaptativa

Sem dependências de ML nesta fase — `requirements.txt` só precisa de `pandas` e `requests`.

**Como a heurística funciona (`heuristic.py`):**
```
1. Baseline por janela de tempo: EWMA (média móvel exponencial) por combinação
   dia-da-semana + faixa de horário (ex: "terça 14h-14h05 costuma ter ~200ms")
2. Desvio robusto: EWMA do desvio absoluto (MAD) em vez de desvio-padrão puro,
   pra não ser distorcido por outliers isolados
3. Anomalia: z-score = (valor_atual - EWMA_bucket) / MAD_bucket
   risk_score = função do z-score + comparação EWMA curta vs. EWMA longa (detecta
   tendência sustentada sem precisar de changepoint detection completo)
4. Threshold (quantos desvios disparam alerta) é ajustável por bucket, e é
   justamente o que o feedback humano (Fase 4) recalibra ao longo do tempo
```

- `collect_and_predict.py` funcional: coleta real do Nebula Logger, roda a heurística, gera `latest.json`
- `latest.json` e `history.json` populados a cada execução
- Site no GitHub Pages exibindo risco atual e histórico

### Fase 2 — Severidade e Comunicação
Mesma regra de severidade da versão anterior:
```
risk_score > 0.85           → CRÍTICA
0.70 < risk_score <= 0.85   → ALTA
0.40 < risk_score <= 0.70   → MÉDIA
risk_score <= 0.40          → BAIXA (só loga)
```
Canal de comunicação: sem Apps Script (que tinha `MailApp` nativo), o envio de email a partir do GitHub Actions usa uma Action pronta (ex.: `dawidd6/action-send-mail`) com SMTP configurado via Secrets, ou um webhook do Slack (`curl` simples para a URL do webhook) — ambos triviais de adicionar ao workflow de coleta quando `risk_score` ultrapassa o limiar.

### Fase 3 — Modo Sombra: Prophet/Isolation Forest + Registro Comparativo

**Pré-requisito:** pelo menos algumas semanas de `history.json` real acumulado na Fase 1/2 — sem isso, Prophet ainda sofre do problema de cold-start descrito no início deste documento.

- `shadow_ml.py`: roda Prophet + Isolation Forest no mesmo job de coleta, **sem disparar alerta** — só registra a própria previsão
- `predictions.json` (registro único compartilhado): cada ciclo grava, lado a lado, o score da heurística, o score do modelo sombra, e (quando confirmado depois) o resultado real:
```json
{
  "timestamp": "2026-09-01T14:05:00Z",
  "service": "integration_xyz",
  "heuristic_score": 0.72,
  "heuristic_alerted": true,
  "shadow_prophet_score": 0.81,
  "shadow_isolation_forest_anomaly": true,
  "actual_incident": null
}
```
- `compare_models.py`: calcula, com base no `predictions.json`, a precisão recente de cada abordagem (heurística vs. modelo sombra) nos incidentes já confirmados — **estatística simples (precisão/recall por janela móvel), sem LLM envolvido** — e expõe esse comparativo no dashboard
- **Promoção do modelo sombra a principal é uma decisão manual, documentada**, tomada quando o comparativo mostrar vantagem consistente do Prophet/Isolation Forest ao longo de várias semanas — nunca uma troca automática silenciosa
- `requirements.txt` passa a incluir `prophet` e `scikit-learn` só a partir desta fase

### Fase 4 — Feedback Contínuo
- Loop de feedback via Issues já detalhado acima
- `weekly_retrain.py` roda em cron semanal, lê `feedback.json` + `predictions.json`: ajusta o threshold por bucket da heurística e, se o modo sombra já estiver ativo, recalibra `contamination` do Isolation Forest e re-treina o Prophet
- Indicador de saúde no dashboard: como não existe mais "Colab dormindo", o indicador passa a ser **"dados desatualizados"** — se o `timestamp` do `latest.json` estiver mais velho que o esperado (ex.: >15 min), o front-end mostra um banner de alerta. Isso cobre falhas reais (Salesforce fora do ar, rate limit, workflow falhando) sem o risco de sessão que o Colab tinha.

### Fase 5 — Hardening
- Paginação SOQL se o volume de logs ultrapassar 2.000 registros (`nextRecordsUrl`)
- Retry com backoff exponencial nas chamadas ao Salesforce
- Rotina de poda do branch `data` se o histórico de commits crescer demais (squash periódico, sem afetar `master`)
- Rotação de credenciais (Secrets do GitHub)
- Runbook de troubleshooting

---

## DECISÕES TÉCNICAS CRÍTICAS (resumo)

1. **GitHub Actions substitui Apps Script + Colab.** A computação roda no mesmo job que coleta os dados — elimina o segundo salto que existia com o Colab, e com ele o ngrok e a dependência de sessão/navegador aberto.
2. **Heurística adaptativa primeiro, Prophet/Isolation Forest em modo sombra depois.** Evita o problema de cold-start do ML (precisa de semanas de histórico pra ajustar bem) e adia a complexidade de dependências (`prophet`, `scikit-learn`) até haver dado real suficiente pra justificá-la. A troca de modelo principal é decisão manual baseada em comparação empírica, não automática.
3. **Peso entre abordagens por desempenho histórico, não por LLM.** Comparar heurística vs. modelo sombra é um problema estatístico (precisão/recall por janela móvel) — resolvido com aritmética simples sobre o `predictions.json`, sem custo de API, sem latência extra, sem camada caixa-preta.
4. **Branch `data` separado de `master`.** Evita poluir o histórico de código com commits de dados a cada 5 minutos.
5. **GitHub Pages quase não faz redeploy.** O front-end busca dados direto via `raw.githubusercontent.com` do branch `data`, então o site (HTML/CSS/JS) só precisa ser republicado quando a interface muda, não quando os dados mudam.
6. **GitHub Issues é o único mecanismo de escrita.** Usado exclusivamente para o feedback de falso positivo — sem precisar de nenhum backend customizado, usando a própria autenticação do GitHub.
7. **"MCP" continua não sendo chamado diretamente** — o Python do GitHub Actions replica o fluxo OAuth + REST do Salesforce, mesma lógica documentada desde a v1 deste plano.

---

## CRITÉRIOS DE SUCESSO

- Fase 0 conclui em poucos dias, com todos os itens do Definition of Done atendidos
- Fase 1: heurística adaptativa gerando alertas reais, sem dependência de ML, com precisão inicial estimada em ~70% (linha de base a ser medida com dado real, não suposta)
- Fase 2 dispara alerta em menos de 1 minuto após detecção de severidade alta
- Fase 3: modelo sombra (Prophet/Isolation Forest) acumulando histórico comparativo por pelo menos algumas semanas antes de qualquer decisão de promoção
- Fase 4 mostra redução de falsos positivos semana a semana, e o comparativo heurística-vs-sombra é decidido com dado real
- **Custo total: $0/mês** — GitHub Actions e Pages são gratuitos para repositórios públicos, sem qualquer dependência de Colab, ngrok, Apps Script, Google Sheets ou API de LLM
- **Disponibilidade real 24/7** — sem depender de navegador aberto, ao contrário da v1 deste plano
