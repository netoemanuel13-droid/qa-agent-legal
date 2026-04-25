# JARVIS MASTER — Unificador de Workflows n8n

Consolida todos os workflows separados do n8n em um único workflow chamado **JARVIS MASTER**.

## Pré-requisitos

```bash
pip install requests
```

## Configuração

```bash
export N8N_BASE_URL="https://n8n-68n4.srv1583766.hstgr.cloud"
export N8N_API_KEY="sua_api_key_aqui"
```

## Execução (ordem obrigatória)

### Passo 1 — Exportar e fazer backup de todos os workflows

```bash
python export_workflows.py
```

Salva todos os workflows como JSON em `backup/`.

### Passo 2 — Unificar no JARVIS MASTER

```bash
python unify_workflows.py
```

- Lê os JSONs de `backup/`
- Reposiciona nós por grupo (cada workflow em uma faixa Y exclusiva)
- Resolve conflitos de nomes de nós
- Faz PATCH no JARVIS MASTER via API
- Ativa o workflow

### Passo 3 — Deletar duplicados (SOMENTE após confirmar que está funcionando)

```bash
python delete_duplicates.py
```

Pede confirmação explícita antes de deletar. **Irreversível.**

## Layout do canvas após unificação

| Workflow               | Faixa Y       |
|------------------------|---------------|
| JARVIS MASTER (base)   | 0 – 399       |
| JARVIS Entry           | 400 – 799     |
| JARVIS TTS             | 800 – 1199    |
| JARVIS Chat            | 1200 – 1599   |
| Health Monitor VPS     | 1600 – 1999   |
| Telegram JARVIS        | 2000 – 2399   |
| Telegram OpenClaw      | 2400 – 2799   |
| E-book                 | 2800 – 3199   |
| Instagram QA           | 3200 – 3599   |
| OmniChat               | 3600 – 3999   |
| Meta Ads               | 4000 – 4399   |

## Arquivos gerados

```
backup/
├── _index.json                  # Índice de todos os workflows exportados
├── _unified_payload.json        # Payload enviado ao JARVIS MASTER (backup)
├── jarvis_master__<id>.json
├── jarvis_entry__<id>.json
└── ...
```
