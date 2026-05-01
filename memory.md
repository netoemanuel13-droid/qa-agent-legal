# memory.md — QA Agent Legal
_Última atualização: 2026-05-01_

==================================================
ESTADO ATUAL
==================================================

- Projeto: site estático de páginas legais do QA Agent Bot (TikTok OAuth)
- Deploy: Vercel
- Branch ativa: claude/debug-code-issues-BAVFI
- Status: operacional

==================================================
FATOS CONFIRMADOS
==================================================

- Stack: HTML puro, sem framework, sem build step
- Arquivos presentes: index.html, callback.html, callback, terms.html, privacy.html, vercel.json, SOUL.md
- A rota /callback está configurada no vercel.json com rewrite para callback.html
- TikTok OAuth callback funcional: extrai o code da URL e exibe para o usuário copiar
- Arquivo de verificação TikTok presente: tiktokogpuCfHdlucwzEpFdPYctydtAG1EP3vw.txt
- SOUL.md criado com identidade e comportamento do agente

==================================================
DECISÕES TOMADAS
==================================================

- Provedor LLM: OpenRouter
- Modelo principal: nousresearch/hermes-3-llama-3.1-405b
- Compatibilidade de API: OpenAI-compatible (base_url: https://openrouter.ai/api/v1)
- SOUL.md salvo na raiz do repositório
- API Key do OpenRouter: configurar localmente (nunca commitar)

==================================================
PENDÊNCIAS
==================================================

- [ ] STYLE.md ainda não criado
- [ ] OpenClaw não está instalado neste ambiente (configurar na máquina local)
- [ ] API Key deve ser configurada localmente via: openclaw config set api_key SUA_CHAVE
- [ ] Testar conexão com Hermes 3 após configuração local

==================================================
RISCOS
==================================================

- A API Key do OpenRouter foi exposta em chat — REVOGAR e gerar nova imediatamente
- Não há autenticação no callback OAuth além do próprio fluxo TikTok
- Sem CI/CD configurado — deploys são manuais via Vercel

==================================================
PRÓXIMOS PASSOS
==================================================

1. Revogar a API Key exposta no OpenRouter
2. Instalar OpenClaw localmente: pip install openclaw
3. Configurar OpenClaw:
   openclaw config set provider openai
   openclaw config set base_url https://openrouter.ai/api/v1
   openclaw config set model nousresearch/hermes-3-llama-3.1-405b
   openclaw config set api_key NOVA_CHAVE
4. Copiar SOUL.md para a pasta de configuração do OpenClaw (~/.openclaw/)
5. Testar: openclaw chat "Olá, você está funcionando?"

==================================================
NOTAS PARA CONTINUIDADE
==================================================

- O agente opera com identidade definida no SOUL.md
- O usuário gerencia conteúdo e evolução do projeto diretamente
- Qualquer nova sessão deve carregar este memory.md para contexto imediato
