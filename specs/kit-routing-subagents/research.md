<!-- research.md | Vitalia SDD v0.6.0 | 17-10-2026 10:28(GMT-04:00) -->
# Technical Research & Grounding: kit-routing-subagents

Este documento consolida a fundamentação técnica e verificação de fontes externas autoritativas para as decisões arquiteturais da feature `kit-routing-subagents`, atendendo rigorosamente ao Princípio Constitucional P03 (*External Verification Protocol*).

---

## Decisão 1: Validação Estrita de Contratos de Handoff com JSON Schema Draft-07
- **Escolhido**: Biblioteca padrão `jsonschema` (versão 4.23+ com suporte a Draft-07 RFC)
- **Verificado em**: https://pypi.org/project/jsonschema/ e https://json-schema.org/specification em 17-10-2026
- **Justificativa**: A biblioteca `jsonschema` é o padrão da indústria para validação sintática e semântica de contratos de troca de mensagens. Ela oferece validação determinística sem dependências de compilação C complexas, garantindo que nenhum payload corrompido ou injetado alcance o contexto dos modelos LLM (atendendo OWASP LLM01:2025 e Princípio P12).
- **Alternativas**:
  - `pydantic v2`: Rejeitado para o módulo de handoff de transporte do kit para evitar introduzir dependência rígida de compilação Rust em ambientes heterogêneos locais (Princípio P11).
  - `fastjsonschema`: Rejeitado por gerar código compilado dinâmico em tempo de execução, o que adiciona risco de segurança e complexidade desnecessária para o volume de handoffs locais.

---

## Decisão 2: Ledger Local de Handoffs em Filesystem Transacional (Zero Data Leak)
- **Escolhido**: Persistência isolada em `.vitalia/memory/data_storage/handoffs/handoff_<uuid>.json` com mutação de estado atômico via `os.replace`
- **Verificado em**: https://docs.python.org/3/library/os.html#os.replace e Diretrizes de Privacy by Design LGPD Art. 11/48 em 17-10-2026
- **Justificativa**: A gravação em disco local do repositório garante isolamento hermético entre múltiplos projetos mantidos na mesma máquina. A operação `os.replace` é atômica no nível do sistema de arquivos POSIX, prevenindo concorrência e condições de corrida durante a transição do status de `"pending"` para `"consumed"`.
- **Alternativas**:
  - `Redis Streams (vitalia:handoffs)`: Congelado temporariamente nesta fase para assegurar autonomia 100% offline e zero dependência de daemons externos ativos em ambiente de desenvolvimento.
  - Diretório temporário do sistema (`/tmp` ou `~/.vitalia/tmp`): Categoricamente rejeitado por violar o isolamento de privacidade e expor metadados proprietários a outros processos do host (vazamento de dados).

---

## Decisão 3: Protocolo Supervisor/Dispatcher Socrático Desacoplado
- **Escolhido**: Padrão Supervisor Desacoplado com triagem por Dispatcher determinístico em 2 níveis (`routing_table.yaml` + `brainstorming_intents.yaml`)
- **Verificado em**: https://github.com/langchain-ai/langgraph-supervisor-py e https://platform.openai.com/docs/guides/agents em 17-10-2026
- **Justificativa**: Desacoplar o supervisor socrático (`brainstorming`) da responsabilidade de despacho (`vitalia-route`) garante separação estrita de preocupações. O supervisor foca em clarificação de escopo e gera uma síntese Markdown editável pelo humano (HITL), enquanto o dispatcher resolve rotas canônicas e escalação invertida.
- **Alternativas**:
  - Roteamento inline direto no Brainstorming: Rejeitado por sobrecarregar o prompt do supervisor com tabelas de roteamento gigantescas e criar acoplamento temporal rígido.
  - Multi-agente autônomo sem intervenção humana: Rejeitado por violar a soberania humana inviolável (Princípio P00 e EU AI Act Art. 14).

---

## Decisão 4: Equalização de Contexto e Poda Semântica Sensível ao Hardware Profile
- **Escolhido**: Subsistema nativo de cotas calibradas (`total_budget` + `source_weights`) com poda semântica orientada ao `hardware_profile` (`frontier` vs `lightweight`)
- **Verificado em**: Padrões de Context Window Economics em Claude Code / Antigravity e Qwen2.5 Context Architecture em 17-10-2026
- **Justificativa**: Modelos de fronteira na IDE (Claude 3.5 Sonnet, Gemini Pro) operam com janelas amplas (128k a 1M tokens), necessitando de contexto rico para orquestração. Modelos locais (Qwen2.5 3B no Ollama) possuem orçamento restrito de tokens e VRAM, degradando em prompts acima de 4000 tokens. A sensibilidade ao hardware profile adapta o `total_budget` garantindo máxima eficiência em ambos os cenários.
- **Alternativas**:
  - Limite rígido universal de 1000 tokens: Rejeitado por asfixiar desnecessariamente os modelos de fronteira na IDE.
  - Truncamento cego de strings brutas: Rejeitado por quebrar estruturas JSON/YAML válidas (Princípio P16).

---

## Decisão 5: Nomenclatura Idempotente no Instalador de Projeto
- **Escolhido**: Transformação determinística via regex `clean_name=$(echo "${ext_name}" | sed 's/^vitalia-//')` com interpolação canônica `vitalia-${clean_name}`
- **Verificado em**: GNU Bash Manual - Parameter Expansion & Sed Stream Editor Standards em 17-10-2026
- **Justificativa**: Garante que extensões que já contêm o prefixo `vitalia-` (ex: `vitalia-route.toml`) gerem diretórios de skill perfeitamente idempotentes em `.agents/skills/vitalia-route/`, eliminando duplicações como `vitalia-vitalia-*`.
- **Alternativas**:
  - Renomear arquivos TOML originais: Rejeitado para preservar compatibilidade com invocações existentes no ecossistema global.
