# Salesforce MCP Authentication Kit

Kit de autenticação **pronto para replicar** em qualquer projeto que consuma os
**Salesforce Hosted MCP servers** (`api.salesforce.com/platform/mcp/v1/...`) via
OAuth2 com **Refresh Token Rotation automática** em GitHub Actions.

Este kit nasceu de um projeto real (monitoramento preditivo Salesforce) e
contém **os códigos exatos que funcionaram em produção**, sem nenhum secret —
você só precisa dos valores da sua própria External Client App.

---

## O problema resolvido

1. Os Salesforce Hosted MCP servers **não aceitam** Connected App legada nem
   redirect URI em HTTP puro. Só funcionam com **External Client App** +
   PKCE + JWT-based access tokens.
2. O org pode impor **Refresh Token Rotation obrigatória** (não desligável) —
   a cada refresh, o Salesforce **mata o refresh token anterior** e entrega um
   novo. Qualquer pipeline agendado que guarda o token fixo em secret **quebra
   no segundo run** com `invalid_grant`.
3. Solução: o próprio pipeline **devolve o token rotacionado** para o secret do
   GitHub em cada execução (via PAT fine-grained). Loop auto-sustentável.

```
 ┌─────────────────────────  GitHub Actions (cron */15)  ─────────────────────────┐
 │                                                                                │
 │  1. secrets.SF_REFRESH_TOKEN ──► SalesforceClient.__init__                     │
 │  2. 401/refresh ──► POST token_endpoint (grant_type=refresh_token)             │
 │        └─► Salesforce ROTACIONA o token: devolve access + NOVO refresh          │
 │  3. cliente atualiza self.refresh_token = novo                                  │
 │  4. pipeline executa (SOQL/MCP tools)                                           │
 │  5. finally: --auth-state-out grava {"refresh_token": novo}                    │
 │  6. passo "Rotate auth secret" (GH_PAT) lê o arquivo e roda                     │
 │        gh secret set SF_REFRESH_TOKEN --body "$NOVO"                            │
 │        └─► próximo run já começa com o token atual                              │
 └─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Estrutura do kit

| Arquivo | Papel |
|---|---|
| `scripts/get_sf_mcp_tokens.py` | Bootstrap OAuth2 PKCE (gera o 1º refresh token) |
| `client/salesforce_mcp_client.py` | Client MCP self-contained (Streamable HTTP + retry + rate limit + refresh/rotação automática) |
| `workflow/collect.yml` | Workflow real de referência (rotação do secret + persistência de snapshot) |
| `pipeline/run_with_rotation.py` | Padrão try/finally + `--auth-state-out` para qualquer script |
| `docs/TROUBLESHOOTING.md` | Todos os erros reais encontrados e as causas |

---

## Pré-requisitos (setup na Salesforce, 5 min)

1. **Setup → App Manager → New Connected App → External Client App**
   (o tipo certo é *External Client App*, não o legado).
2. Configuração obrigatória:
   - **OAuth scopes**: `api`, `sfap_api`, `refresh_token` (e `mcp_api` se o
     server MCP pedir — o bootstrap já envia os 4)
   - **Require Proof Key for Code Exchange (PKCE)**: ✅ ativado
   - **Issue JSON Web Token (JWT)-based access tokens for named users**: ✅
   - **Refresh Token Policy**: prefira *Expire refresh token if not used for
     specific time* (padrão)
   - Anote **Consumer Key** e **Consumer Secret** (ficam na página do app).
3. **Refresh Token Rotation**: se o org marcar como obrigatório (campo
   bloqueado: *"To change this required setting, contact Support"*), **não
   lute contra** — este kit já foi desenhado para esse cenário.

> External Client Apps **não aceitam redirect URI em HTTP puro**. O script usa
> o callback oficial `https://login.salesforce.com/services/oauth2/success` e
> você cola o `code` manualmente — sem precisar de servidor local.

---

## Passo a passo

### 1. Gerar o refresh token inicial

```bash
python scripts/get_sf_mcp_tokens.py "<CONSUMER_KEY>" "<CONSUMER_SECRET>"
```

- Abre o navegador com a URL de autorização → aprova → cai na página de
  sucesso do Salesforce.
- Cole a URL final (ou só o `?code=...`) no terminal.
- O script valida `state` (anti-CSRF) e imprime o **refresh token** — nunca o
  access token completo.

### 2. Gravar os secrets no GitHub

```bash
gh secret set SF_CLIENT_ID <<< '<CONSUMER_KEY>'
gh secret set SF_CLIENT_SECRET <<< '<CONSUMER_SECRET>'
gh secret set SF_REFRESH_TOKEN <<< '<refresh token impresso no passo 1>'
gh secret set SALESFORCE_MCP_URL <<< 'https://api.salesforce.com/platform/mcp/v1/platform/sobject-reads'
```

O `SALESFORCE_MCP_URL` aponta para o server MCP desejado
(`sobject-all`, `sobject-reads`, `lens-explorer`, ...). Se já usa em outro
projeto, reaproveite a URL.

### 3. Criar o PAT fine-grained (só para a rotação do secret)

O `GITHUB_TOKEN` de Actions **não consegue** atualizar secrets. Crie um PAT:

- GitHub → Settings → Developer settings → **Fine-grained personal access
  tokens** → Generate new token
- **Repository access**: *Only select repositories* → escolha o repo
- **Permissions → Repository permissions**:
  - **Secrets → Read and write** ⚠️ *(o correto — "Actions" não é necessário;
    Metadata é adicionada automaticamente e é obrigatória)*
- Expiração: opcional (sem expiração = menos manutenção, decida você)
- Grave o token como secret: `gh secret set GH_PAT`

### 4. Adicionar o workflow

Copie `workflow/collect.yml` para `.github/workflows/` e adapte:

- `python monitoring/orchestrate.py` → o seu script (ex.: `python app/main.py`)
- `--auth-state-out out/auth_state.json` → **mantenha** (é o contrato com o
  passo de rotação)
- Instale as dependências do seu projeto no passo *Install dependencies*
- Remova os passos que não usar (persistência de snapshot, artefatos)

O passo que faz o segredo virar autônomo é este (já no workflow):

```yaml
      - name: Rotate auth secret (refresh token rotation)
        if: always()
        env:
          GH_TOKEN: ${{ secrets.GH_PAT }}
        run: |
          set -e
          if [ -z "$GH_TOKEN" ]; then
            echo "GH_PAT not configured - skipping secret rotation"; exit 0
          fi
          if [ ! -f "out/auth_state.json" ]; then
            echo "No auth_state.json - nothing to rotate"; exit 0
          fi
          NEW_TOKEN=$(python -c "import json;print(json.load(open('out/auth_state.json'))['refresh_token'])")
          if [ -z "$NEW_TOKEN" ]; then
            echo "Empty refresh token in auth_state.json - skipping"; exit 0
          fi
          gh secret set SF_REFRESH_TOKEN --body "$NEW_TOKEN"
          echo "SF_REFRESH_TOKEN rotated"
```

### 5. Validar

```bash
gh workflow run collect.yml          # 1º run manual
gh run watch                         # sucesso em pipeline + rotate + persist
gh secret list                       # SF_REFRESH_TOKEN com timestamp NOVO
                                    #  (prova que rotacionou)
gh workflow run collect.yml          # 2º run: usa o token rotacionado
```

Se o 2º run for verde, o ciclo está provado — o cron mantém sozinho.

---

## Como o client rotaciona (o coração do kit)

`client/salesforce_mcp_client.py` (código real, self-contained):

```python
def _refresh_token(self) -> None:
    token_endpoint = self._discover_token_endpoint()
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": self.refresh_token,
        "client_id": self.client_id,
        "client_secret": self.client_secret,
    }
    ...  # POST urlencoded no token_endpoint
    self.token = body["access_token"]
    new_refresh = body.get("refresh_token")
    if new_refresh and new_refresh != self.refresh_token:
        self.refresh_token = new_refresh   # ← captura a rotação
```

E o chamador (padrão em `pipeline/run_with_rotation.py`) **sempre** devolve o
token para o secret, em sucesso E em falha:

```python
client = _build_client()          # criado ANTES do try
try:
    run_pipeline(client=client)   # faz refresh/rotação internamente
finally:
    if args.auth_state_out and client.refresh_token:
        _write_auth_state(args.auth_state_out, client.refresh_token)
```

---

## Armadilhas documentadas (você não vai cair duas vezes)

| Sintoma | Causa | Fix |
|---|---|---|
| `403 invalid_scope ... unknown_error %3D` | scope `sfap_api` faltando no consent | refazer bootstrap com os 4 scopes |
| `invalid_grant` no 2º run do cron | RTR obrigatória matou o token fixo | kit de rotação automática |
| `FileNotFoundError: 'out/previous.json'` | `cd pasta && script` com caminho relativo à raiz | rodar da raiz, caminhos `out/...` |
| `src refspec data does not match any` | `git worktree add ... origin/data` = detached HEAD | `git push origin HEAD:data` |
| Cron `*/15` não dispara no minuto certo | GitHub atrasa/pula slots de schedule sob carga | normal; `workflow_dispatch` para validar |
| `GITHUB_TOKEN` não seta secret | permissão insuficiente por design | PAT fine-grained Secrets read/write |

Detalhes completos em `docs/TROUBLESHOOTING.md`.

---

## Segurança

- **Nenhum secret neste kit** — Consumer Key/Secret/refresh token entram
  apenas como argumentos/env vars/secrets do GitHub.
- O access token nunca é impresso pelo bootstrap (só os 12 primeiros chars).
- Secrets vivem em `gh secret` / GitHub Actions — nunca em arquivos do repo.
- O PAT fine-grained é escopado a 1 repo e 1 permissão (Secrets read/write).