# Salesforce Predictive Monitoring

Monitor preditivo de risco da integração MCP do Salesforce (sobject-reads).

## O que é

Pipeline de coleta contínua que consulta logs reais do Salesforce via MCP
(`Log__c`), calcula um risk score por heurística, compara com a janela
anterior e publica snapshots JSON na branch `data/` a cada 15 minutos
(GitHub Actions). Não há página de dashboard pública ainda — o consumo
visual dos dados é fase futura.

## Artefatos

| Item | Onde |
|---|---|
| Spec e métricas de validação | [`SPECIFICATION.md`](SPECIFICATION.md) |
| Roadmap mestre | [`PROJECT_ROADMAP_MASTER.md`](PROJECT_ROADMAP_MASTER.md) |
| Snapshot mais recente | [`data/` (branch data)](https://github.com/brunotrolo/Salesforce_PredictiveMonitoring/tree/data) |
| Fetcher de dados (com testes) | `site/api/client.js` |

## Estado atual

- Cron 15-min rodando e validado 24/7 (sobrevive à rotação de refresh token).
- Fetcher `site/api/client.js` validado por testes (fallback para mock offline).
- Dashboard HTML: **fora do escopo da Fase 1** — página ainda não publicada.
