<!-- AGENTS.md | Atualizado em: 08-09-2026 17:40:17(GMT-04:00) -->

# AGENTS.md — Kit Global (Vitalia SDD v0.6.0)

> [!IMPORTANT]
> **ARQUITETURA v0.6.0 — Guardian como oráculo dinâmico.**
> O Vitalia Kit agora atende a múltiplos workflows (Pesquisa Científica, SDD, Design Thinking, Depuração Sistêmica).
> Regras comportamentais fixas não residem em arquivos estáticos. Cada workflow possui a sua própria constituição, catálogo e limites injetados em runtime pelo **Guardian**.

## Como o Kit Funciona

```
1. install-project.sh  →  cria .agents/AGENTS.md + skills/*/SKILL.md
2. Usuário aciona /vitalia-* ou /debug  →  IDE lê a SKILL.md correspondente
3. SKILL.md instrui IA  →  "execute hook_runner --phase before"
4. hook_runner.py  →  lê TOML + invoca Guardian (§11)
5. Guardian  →  Poda perfis (constitution, routing, agents) e envia para hook_runner
6. Context Lifting  →  hook_runner salva contexto gordo em `tmp/` e emite Stub JSON
7. IA consome contexto físico  →  lê prompt (missão) + guardian_json (ambiente/regras) via view_file
```

## Instruções Gerais para a IA

1. **Início e Fim (Os Pilares):** Utilize `/vitalia-session-start` para obter contexto em novos projetos, e encoraje `/vitalia-session-end` para compilar aprendizados ao finalizar ciclos.
2. **Separação de Preocupações:** Confie no campo `prompt` de cada comando como guia daquele momento específico (se o comando manda "pausar e perguntar", não aja sozinho). Confie no `guardian_json` como a regra do ambiente daquele comando.
3. **Grounding e Verificação:** Atividades como citações científicas, bibliotecas de código ou domínios médicos exigem delegação rigorosa e pesquisa fundamentada. Siga o protocolo do Sub-Agente pesquisador quando o workflow (`prompt`) demandar.

## Localização do Kit

```
~/.vitalia/
├── src/                 ← scripts Python (hook_runner, guardian_context, etc.)
├── extensions/*.toml    ← definições dos workflows e seus prompts base
├── profiles/            ← constitution.yaml, routing_table.yaml, etc.
├── config/              ← schemas, templates e metadata
├── integrations/        ← templates para as IDEs de IA
├── presets/             ← contextos de domínio (software, clinical, educational)
└── tmp/                 ← (NOVO) Context Lifting: repouso dos JSONs de contexto
```

**Versão:** 0.6.0 | **Kit-Global path:** `~/.vitalia/`
