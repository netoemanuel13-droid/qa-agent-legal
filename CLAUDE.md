# QA Agent Legal — Projeto

## Sobre
Site de páginas legais e OAuth callback para o **QA Agent Bot** — ferramenta de publicação automática de conteúdo com IA para redes sociais.

## Estrutura
```
qa-agent-legal/
├── index.html        ← Landing page do bot
├── terms.html        ← Termos de Serviço
├── privacy.html      ← Política de Privacidade
├── callback.html     ← OAuth callback do TikTok
└── vercel.json       ← Deploy no Vercel
```

## Deploy
- Plataforma: **Vercel**
- Rota `/callback` → `callback.html` (via rewrite no vercel.json)

## Branch de desenvolvimento
Sempre usar: `claude/setup-vps-access-PyY4V`
Nunca fazer push direto para `master` sem permissão explícita.

## Navegação de Contexto
Quando precisar entender código ou arquivos deste projeto:
1. SEMPRE consulte o grafo de conhecimento primeiro: `/graphify query "sua pergunta"`
2. Só leia arquivos brutos se o usuário disser explicitamente "leia o arquivo"
3. Use `graphify-out/wiki/index.md` como ponto de entrada para navegar pela estrutura

## Setup de Otimização de Tokens (Graphify + wiki-brain)
Configurado em `~/.claude/`:
- **Graphify** — grafo de conhecimento persistente (71x menos tokens)
- **wiki-brain** — base de conhecimento que cresce entre sessões
- **Hook SessionEnd** — reconstrói o grafo automaticamente quando arquivos mudam

Para construir/atualizar o grafo: `/graphify .`
Para ativar o wiki-brain: `/wiki-brain`
