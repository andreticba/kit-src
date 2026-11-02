<!-- spec.md | Vitalia SDD v0.6.0 | 20-10-2026 09:50(GMT-04:00) -->
> **spec.md | Vitalia SDD v0.6.0 | 20-10-2026 09:50(GMT-04:00)**
# Especificação de Funcionalidade: Roteamento Inteligente, Handoff Local Seguro e Acionamento de Agentes

**Data:** 18-10-2026 00:45(GMT-04:00)  
**Feature:** `kit-routing-subagents`  
**Status:** DRAFT_REVISION (Alinhado à Constituição e Topologia Bidirecional)  
**Artefatos Relacionados:**
- [handoff_transition_topology.md](file:///home/andre/projetos/assistidos/kit_src/specs/kit-routing-subagents/handoff_transition_topology.md)
- [contracts/toml_workflow_contracts.md](file:///home/andre/projetos/assistidos/kit_src/specs/kit-routing-subagents/contracts/toml_workflow_contracts.md)
- [contracts/handoff_cli_contract.md](file:///home/andre/projetos/assistidos/kit_src/specs/kit-routing-subagents/contracts/handoff_cli_contract.md)
- [research-brainstorming.md](file:///home/andre/projetos/assistidos/kit_src/specs/kit-routing-subagents/research-brainstorming.md)
- [kit_routing_audit.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-distributed/kit_routing_audit.md)
- [vitalia-handoff-v1.0.0.json](file:///home/andre/projetos/assistidos/kit_src/source/src/schemas/vitalia-handoff-v1.0.0.json)
- [ADR-001: Desacoplamento do Redis e Ledger Local de Handoffs](file:///home/andre/projetos/assistidos/kit_src/docs/adr/ADR-001-handoff-local-desacoplado-redis.md)
- [ADR-002: Persistência Segura e Isolamento Zero Data Leak](file:///home/andre/projetos/assistidos/kit_src/docs/adr/ADR-002-persistencia-e-isolamento-zero-data-leak.md)
- [ADR-003: Validação Pré-Hook com Schema JSON Formal](file:///home/andre/projetos/assistidos/kit_src/docs/adr/ADR-003-validacao-pre-hook-com-schema-json.md)
- [ADR-004: Protocolo de Escalação Invertida e Soberania HITL](file:///home/andre/projetos/assistidos/kit_src/docs/adr/ADR-004-escalacao-invertida-e-soberania-hitl.md)
- [ADR-005: Catálogo com Status Operacional e Ingestão AI-Control](file:///home/andre/projetos/assistidos/kit_src/docs/adr/ADR-005-catalogo-com-status-operacional-active-planned.md)
- [ADR-006: Instalador Idempotente e Poda de Tokens no Guardian](file:///home/andre/projetos/assistidos/kit_src/docs/adr/ADR-006-instalador-idempotente-e-poda-de-tokens.md)

---

## 1. Contexto e Objetivo (O Quê e Por Quê)

Uma auditoria aprofundada no sistema de roteamento do Vitalia Kit ([kit_routing_audit.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-distributed/kit_routing_audit.md)) revelou que o kit operava sob uma única primitiva de execução (`IDE → SKILL.md → hook_runner → LLM`), sem mecanismos reais de transferência de contexto entre workflows e agentes (handoff) ou acionamento de sub-agentes. O comando `vitalia-route` encontrava-se isolado sem nenhum caminho de código que o invocasse (A1), o `brainstorming` ignorava a existência do roteador (A2), o instalador gerava comandos com prefixo duplicado `vitalia-vitalia-*` (A3), e o prompt do route instruía o LLM a declarar falsamente a gravação de eventos em um stream Redis inexistente (A4 - violação do Princípio P12). Além disso, o catálogo de agentes continha registros puramente declarativos sem arquivos executáveis (A5, A6) e os adaptadores de contexto excediam o orçamento de tokens (A10).

O objetivo desta especificação é estruturar uma **arquitetura de roteamento e handoff inter-agente local, determinística e segura**, resolvendo integralmente os achados A1 a A11 da auditoria. A solução congela temporariamente o uso do Redis, implementando um **Ledger Local de Handoffs** baseado no schema validado [`vitalia-handoff-v1.0.0.json`](file:///home/andre/projetos/assistidos/kit_src/source/src/schemas/vitalia-handoff-v1.0.0.json), gravado estritamente em `.vitalia/memory/data_storage/handoffs/` sob a nomenclatura canônica `handoff_<source_workflow>_to_<target_workflow>_<uuid_8>.json` (Zero Data Leak). O Brainstorming é desacoplado da responsabilidade de roteamento, atuando como supervisor socrático que delega para o `vitalia-route`. O `vitalia-route` passa a operar como dispatcher oficial com suporte a fluxo bidirecional (incluindo despacho para especialistas do catálogo e escalação invertida quando agentes de execução extrapolam seu domínio). O catálogo de agentes é saneado com `status: active | planned`, incorporando a equipe multidisciplinar do **AI-Control** (`Master AI-Control`, `Django-Stark`, `React-Vinci`, `Infra-Nomad`, `Cortex-Analyst`, `Figma-Maestro`).

---

## 2. Requisitos Funcionais (FR-xxx)

### FR-001: Módulo Utilitário de Handoff Local (`vitalia_handoff.py`)
- **Descrição:** O sistema **MUST** fornecer um módulo utilitário em Python (`source/src/vitalia_handoff.py`) utilizável tanto como biblioteca quanto como ferramenta CLI, com funções determinísticas para:
  1. `create()`: gerar payloads de handoff completos salvos obrigatoriamente no padrão semântico `handoff_<source_workflow>_to_<target_workflow>_<uuid_8>.json`, contendo UUID v4 único (`handoff_id`), timestamp ISO8601 no fuso America/Cuiaba (`GMT-04:00`), `machine_id` SHA256[:8], `ttl_seconds: 3600` e o campo obrigatório `envelope.direction` com enum restrito a `["forward", "reverse", "fallback"]` (onde entradas diretas do usuário ou fluxos progressivos assumem `"forward"`);
  2. `validate()`: validar sintática e estruturalmente o arquivo JSON contra o schema [`vitalia-handoff-v1.0.0.json`](file:///home/andre/projetos/assistidos/kit_src/source/src/schemas/vitalia-handoff-v1.0.0.json);
  3. `consume()`: realizar a mutação atômica do campo `envelope.status` de `"pending"` para `"consumed"` via arquivo temporário + `os.replace`;
  4. `get_latest()`: localizar o último handoff pendente válido em `.vitalia/memory/data_storage/handoffs/`.
- **Impacto ao Usuário (P02):** Previne erros manuais de JSON, discrepâncias de contrato e falhas de transferência de contexto, assegurando transições transparentes e sem atrito entre comandos na IDE.
- **Conformidade Constitucional (P00-P17):** Ferramenta interna de desenvolvimento de software do repositório local. Não processa dados clínicos, biomarcadores ou dados pessoais identificáveis (P07 e P09 não aplicáveis). Auditabilidade técnica e linhagem asseguradas (P14 e P17). Nenhum princípio da rubrica é violado.
- **Referência Arquitetural (ADR):** [ADR-001: Desacoplamento do Redis e Ledger Local de Handoffs](file:///home/andre/projetos/assistidos/kit_src/docs/adr/ADR-001-handoff-local-desacoplado-redis.md).

### FR-002: Persistência Segura e Isolamento de Handoffs em `data_storage` (Zero Data Leak)
- **Descrição:** O sistema **MUST** gravar todos os arquivos temporários de handoff estritamente no diretório de armazenamento persistente do projeto local em `.vitalia/memory/data_storage/handoffs/handoff_<source_workflow>_to_<target_workflow>_<uuid_8>.json`. O sistema **MUST NOT** gravar arquivos de handoff em diretórios globais do sistema (`~/.vitalia/tmp` ou `/tmp`).
- **Impacto ao Usuário (P02):** Garante a soberania total dos dados e do código-fonte do projeto, impedindo vazamento de contexto proprietário ou colisão acidental entre diferentes repositórios na mesma máquina de desenvolvimento.
- **Conformidade Constitucional (P00-P17):** Ferramenta interna de desenvolvimento de software do repositório local. Não processa dados clínicos, biomarcadores ou dados pessoais identificáveis (P07 e P09 não aplicáveis). Auditabilidade técnica e linhagem asseguradas (P14 e P17). Nenhum princípio da rubrica é violado.
- **Referência Arquitetural (ADR):** [ADR-002: Persistência Segura e Isolamento Zero Data Leak](file:///home/andre/projetos/assistidos/kit_src/docs/adr/ADR-002-persistencia-e-isolamento-zero-data-leak.md).

### FR-003: Validação Pré-Hook Obrigatória contra Schema Formal
- **Descrição:** O sistema **MUST** validar com a biblioteca `jsonschema` todo arquivo de handoff antes que seus dados sejam consumidos por qualquer workflow ou modelo LLM. Caso o arquivo viole o contrato [`vitalia-handoff-v1.0.0.json`](file:///home/andre/projetos/assistidos/kit_src/source/src/schemas/vitalia-handoff-v1.0.0.json), a execução **MUST** ser abortada imediatamente com código de saída 1 e mensagem de erro descritiva no stderr.
- **Impacto ao Usuário (P02):** Evita que comandos quebrem no meio do processo ou que o LLM receba entradas malformadas, garantindo previsibilidade e robustez operacional ao desenvolvedor.
- **Conformidade Constitucional (P00-P17):** Ferramenta interna de desenvolvimento de software do repositório local. Não processa dados clínicos, biomarcadores ou dados pessoais identificáveis (P07 e P09 não aplicáveis). Auditabilidade técnica e linhagem asseguradas (P14 e P17). Nenhum princípio da rubrica é violado.
- **Referência Arquitetural (ADR):** [ADR-003: Validação Pré-Hook com Schema JSON Formal](file:///home/andre/projetos/assistidos/kit_src/docs/adr/ADR-003-validacao-pre-hook-com-schema-json.md).

### FR-004: Ingestão Transparente de Handoff no Guardian (`session_context.handoff`)
- **Descrição:** O hook runner (`vitalia_hook_runner.py`) e o motor de contexto do Guardian (`GuardianContextV2`) **MUST** inspecionar os argumentos recebidos (`user_args`). Se uma referência de handoff for detectada (ex: `--handoff=<id>` ou caminho do arquivo), o sistema **MUST** verificar o campo `envelope.status`: se o status for `"pending"` e o payload for válido, o sistema **MUST** injetar o objeto completo em `guardian_json.session_context.handoff`. Se o status for `"consumed"` ou expirado, ou se nenhum argumento de handoff for fornecido, a chave `session_context.handoff` **MUST** ser definida como `null`.
- **Impacto ao Usuário (P02):** Permite transição fluida de contexto mantendo retrocompatibilidade total com as 25 skills existentes sem alterar as assinaturas CLI dos templates `SKILL.md`.
- **Conformidade Constitucional (P00-P17):** Ferramenta interna de desenvolvimento de software do repositório local. Não processa dados clínicos, biomarcadores ou dados pessoais identificáveis (P07 e P09 não aplicáveis). Auditabilidade técnica e linhagem asseguradas (P14 e P17). Nenhum princípio da rubrica é violado.
- **Referência Arquitetural (ADR):** [ADR-001: Desacoplamento do Redis e Ledger Local de Handoffs](file:///home/andre/projetos/assistidos/kit_src/docs/adr/ADR-001-handoff-local-desacoplado-redis.md).

### FR-005: Desacoplamento do Brainstorming como Supervisor Socrático
- **Descrição:** O workflow `/vitalia-brainstorming` **MUST** atuar como o supervisor socrático do ecossistema, operando como ponto de entrada tanto para concepção de novas features (`session_context.user_input`) quanto para repactuação soberana de escopo em retornos de escalação (`session_context.handoff` com `direction: "reverse"`). O Brainstorming **MUST NOT** assumir funções de despacho direto para o pipeline de código. Ao consolidar o consenso com o desenvolvedor, ele **MUST**:
  1. Gerar um arquivo de síntese estruturada da ideação em formato Markdown (`specs/<feature>/research-brainstorming.md`);
  2. Apresentar o documento gerado com destaque visual ao usuário na IDE, permitindo sua revisão e edição soberana (Human-in-the-Loop) antes do avanço;
  3. Gerar o payload de handoff em `.vitalia/memory/data_storage/handoffs/handoff_brainstorming_to_vitalia-route_<uuid_8>.json` com `envelope.direction: "forward"` e `intent_type: "brainstorming_to_route"`, preenchendo obrigatoriamente:
     - `intent.normalized_summary`: contendo o caminho relativo canônico do arquivo de síntese Markdown (`specs/<feature>/research-brainstorming.md`);
     - `intent.source_input`: solicitação original do usuário que disparou a ideação;
     - `intent.detected_domain`: domínio semântico identificado via `brainstorming_intents.yaml`;
     - `intent.feature_context`: caminho do diretório da feature ativa em `specs/`;
     - `intent.confidence`: grau de certeza da classificação ($\ge 0.90$).
  4. Apresentar a instrução formal de acionamento do dispatcher oficial: `/vitalia-route --handoff=<id>`. O Brainstorming **MUST NOT** realizar roteamento direto ou tentar acionar executores de código sem intermediação do dispatcher.
- **Impacto ao Usuário (P02):** Garante controle humano pleno (HITL) sobre o que foi pactuado no debate, reduz a sobrecarga de tokens e previne distorções no repasse de requisitos para os agentes subsequentes.
- **Conformidade Constitucional (P00-P17):** Ferramenta interna de desenvolvimento de software do repositório local. Não processa dados clínicos, biomarcadores ou dados pessoais identificáveis (P07 e P09 não aplicáveis). Auditabilidade técnica e linhagem asseguradas (P14 e P17). Nenhum princípio da rubrica é violado.
- **Referência Arquitetural (ADR):** [ADR-004: Protocolo de Escalação Invertida e Soberania HITL](file:///home/andre/projetos/assistidos/kit_src/docs/adr/ADR-004-escalacao-invertida-e-soberania-hitl.md).

### FR-006: Dispatcher de Roteamento Inteligente Bidirecional (`vitalia-route`)
- **Descrição:** O comando `/vitalia-route` **MUST** atuar como o despachante oficial do ecossistema Vitalia. Ele deve ler o contexto de intenção (seja de `session_context.handoff` ou de entrada direta textual) e consumir as fontes equalizadas pelo Guardian (`guardian_json.sources`):
  1. **Consumo de Handoff e Despacho de Especialistas:** Se acionado via handoff, o roteador analisa a maturidade da concepção. Se o domínio exigir discovery, pesquisa ou conformidade médica, o `vitalia-route` **MUST** propor primeiramente o especialista apropriado do catálogo com `status: "active"` (ex: `/vitalia-design-thinking`, `/vitalia-literature-curator`, `/vitalia-medical-gate`). O avanço para a especificação técnica formal do SDD (`/vitalia-spec-specify`) só deve ser proposto quando a concepção estiver madura ou após a finalização do trabalho dos especialistas (que retornam seu contexto em JSON com `direction: "reverse"`).
  2. **Fallback Preservando Contexto (Nível 3):** Quando acionado diretamente com intenção vaga ou ambígua que exija clarificação socrática, o `vitalia-route` **MUST NOT** enviar o usuário de mãos vazias ao Brainstorming. Ele **MUST** gerar um payload de handoff em `.vitalia/memory/data_storage/handoffs/handoff_vitalia-route_to_brainstorming_<uuid_8>.json` com `envelope.direction: "fallback"`, `intent_type: "route_to_brainstorming"`, encapsulando o texto original em `intent.source_input` e orientar o acionamento de `/vitalia-brainstorming --handoff=<id>`.
  3. **Zero Redis:** O prompt de `vitalia-route.toml` **MUST NOT** alegar gravação em streams Redis. O consumo do handoff de entrada é realizado via mutação atômica em disco (`vitalia_handoff.py consume`).
- **Impacto ao Usuário (P02):** Permite navegação intuitiva entre dezenas de workflows e comandos sem exigir memorização de sintaxes complexas, garantindo que o contexto nunca seja descartado.
- **Conformidade Constitucional (P00-P17):** Ferramenta interna de desenvolvimento de software do repositório local. Não processa dados clínicos, biomarcadores ou dados pessoais identificáveis (P07 e P09 não aplicáveis). Auditabilidade técnica e linhagem asseguradas (P14 e P17). Nenhum princípio da rubrica é violado.
- **Referência Arquitetural (ADR):** [ADR-001: Desacoplamento do Redis e Ledger Local de Handoffs](file:///home/andre/projetos/assistidos/kit_src/docs/adr/ADR-001-handoff-local-desacoplado-redis.md).

### FR-007: Protocolo de Escalação Invertida (`route_to_brainstorming`)
- **Descrição:** O sistema **MUST** suportar o fluxo invertido de escalação operacional para preservação da integridade arquitetural. Aplica-se a qualquer workflow ou agente de execução técnica do SDD (incluindo `/vitalia-spec-implement` e `/vitalia-pair`). Sempre que um agente de execução identificar que uma solicitação do usuário extrapola o escopo técnico estabelecido, introduz novas regras de negócio ou altera decisões arquiteturais registradas formalmente nos ADRs do projeto (`docs/adr/`) ou no ledger de decisões (`.vitalia/memory/session/data/decisions.json`), ele **MUST**:
  1. Interromper imediatamente a geração de código ou alteração de artefatos;
  2. Impor a regra inviolável de que toda modificação arquitetural exige aprovação do desenvolvedor humano (Human-in-the-Loop), sendo expressamente vedado a qualquer agente de IA realizar ou aprovar alterações arquiteturais de forma autônoma;
  3. Gravar o relatório técnico da divergência em `.vitalia/memory/data_storage/handoffs/divergence_<uuid_8>.json`;
  4. Gerar um payload de handoff em `.vitalia/memory/data_storage/handoffs/handoff_<source_workflow>_to_vitalia-route_<uuid_8>.json` com `envelope.direction: "reverse"`, `intent_type: "route_to_brainstorming"`, inserindo em `intent.normalized_summary` o caminho do arquivo de divergência gerado;
  5. Instruir o desenvolvedor a retornar ao ciclo de ideação via `/vitalia-route --handoff=<id>` (ou `/vitalia-brainstorming --handoff=<id>`) para repactuação soberana do escopo e posterior formalização de um novo ADR (`/vitalia-adr`).
- **Impacto ao Usuário (P02):** Impede que o desenvolvedor implemente código fora de especificação acidentalmente no meio de uma sessão de codificação, protegendo o projeto contra dívida técnica não rastreada e erosão arquitetural.
- **Conformidade Constitucional (P00-P17):** Ferramenta interna de desenvolvimento de software do repositório local. Não processa dados clínicos, biomarcadores ou dados pessoais identificáveis (P07 e P09 não aplicáveis). Auditabilidade técnica e linhagem asseguradas (P14 e P17). Nenhum princípio da rubrica é violado.
- **Referência Arquitetural (ADR):** [ADR-004: Protocolo de Escalação Invertida e Soberania HITL](file:///home/andre/projetos/assistidos/kit_src/docs/adr/ADR-004-escalacao-invertida-e-soberania-hitl.md).

### FR-008: Saneamento do Catálogo com Status Operacional (`status: active | planned`)
- **Descrição:** O arquivo `source/profiles/agents_catalog.yaml` e seu esquema de validação **MUST** incorporar o campo `status` com valores restritos ao enum `["active", "planned"]`, com a seguinte semântica estrita:
  1. **`status: "active"`**: Atribuído exclusivamente a entidades que possuam arquivo de extensão `.toml` executável implementado em `source/extensions/<id>.toml` e skill correspondente em `.agents/skills/vitalia-<id>/SKILL.md`. Estão aptas para despacho imediato e execução interativa;
  2. **`status: "planned"`**: Atribuído a entidades formalmente mapeadas no ecossistema e roadmap conceitual, mas cuja extensão executável `.toml` **não** existe em `source/extensions/`. Os 4 agentes legados sem extensão executável (`design-thinking`, `literature-curator`, `visual-creator`, `architect`) e os 6 agentes da equipe AI-Control **MUST** receber o status `planned`.
  3. O adaptador `AgentsCatalogAdapter` e o motor de despacho **MUST** utilizar esse campo para diferenciar entidades executáveis de itens de roadmap, impedindo que o dispatcher proponha o acionamento de extensões não implementadas.
- **Impacto ao Usuário (P02):** Elimina a frustração de tentar rodar comandos que não existem na instalação do kit e provê clareza absoluta sobre o roadmap de capacidades disponíveis.
- **Conformidade Constitucional (P00-P17):** Ferramenta interna de desenvolvimento de software do repositório local. Não processa dados clínicos, biomarcadores ou dados pessoais identificáveis (P07 e P09 não aplicáveis). Auditabilidade técnica e linhagem asseguradas (P14 e P17). Nenhum princípio da rubrica é violado.
- **Referência Arquitetural (ADR):** [ADR-005: Catálogo com Status Operacional e Ingestão AI-Control](file:///home/andre/projetos/assistidos/kit_src/docs/adr/ADR-005-catalogo-com-status-operacional-active-planned.md) e [ADR-006: Instalador Idempotente e Poda de Tokens no Guardian](file:///home/andre/projetos/assistidos/kit_src/docs/adr/ADR-006-instalador-idempotente-e-poda-de-tokens.md).

### FR-009: Ingestão Formal da Equipe AI-Control no Catálogo
- **Descrição:** O arquivo `source/profiles/agents_catalog.yaml` **MUST** incorporar os 6 agentes especialistas extraídos de `AI-Control completo.md`, registrando cada entidade com atributos canônicos e `status: "planned"`:
  1. **`master-ai-control` (Arquiteto de Soluções e Tech Lead Sênior):**
     - Comando: `/vitalia-master-ai-control` | Emoji: `👑` | Model Hint: `frontier`
     - Papel: Orquestrador da arquitetura multi-tenant, decomposição atômica de épicos e guardião dos 17 princípios de desenvolvimento.
     - Inputs: `epic_description` | Outputs: `architecture_blueprint` (markdown) | Queue: `vitalia:agents:master-ai-control`
  2. **`django-stark` (Engenheiro Backend Sênior):**
     - Comando: `/vitalia-django-stark` | Emoji: `⚡` | Model Hint: `frontier`
     - Papel: Implementação de APIs REST com Django 5, DRF, Celery, PostgreSQL 16 + pgvector, isolamento estrito por `organization_id` e RBAC.
     - Inputs: `api_contract` | Outputs: `code` (python) | Queue: `vitalia:agents:django-stark`
  3. **`react-vinci` (Engenheiro Frontend Sênior):**
     - Comando: `/vitalia-react-vinci` | Emoji: `🎨` | Model Hint: `frontier`
     - Papel: Implementação de interfaces com Next.js (App Router), TypeScript, Tailwind CSS, shadcn/ui, TanStack Query e acessibilidade.
     - Inputs: `figma_tokens`, `api_contract` | Outputs: `code` (typescript) | Queue: `vitalia:agents:react-vinci`
  4. **`infra-nomad` (Engenheiro DevOps e Infraestrutura):**
     - Comando: `/vitalia-infra-nomad` | Emoji: `🏗️` | Model Hint: `lightweight`
     - Papel: Configuração de Docker Compose, redes isoladas, volumes persistentes, pipelines de CI/CD e ambientes de produção.
     - Inputs: `environment_config` | Outputs: `docker_compose`, `ci_pipeline` | Queue: `vitalia:agents:infra-nomad`
  5. **`cortex-analyst` (Engenheiro de Dados e IA):**
     - Comando: `/vitalia-cortex-analyst` | Emoji: `🧠` | Model Hint: `heavy`
     - Papel: Pipelines de ingestão documental, chunking contextual, modelos de embeddings e busca semântica com pgvector.
     - Inputs: `document_stream` | Outputs: `vector_embeddings` | Queue: `vitalia:agents:cortex-analyst`
  6. **`figma-maestro` (Designer de Produto e UX/Design System):**
     - Comando: `/vitalia-figma-maestro` | Emoji: `✨` | Model Hint: `lightweight`
     - Papel: Prototipação, arquitetura de design tokens, micro-interações, fluxos de usuário e biblioteca de componentes reutilizáveis.
     - Inputs: `wireframe` | Outputs: `design_tokens` | Queue: `vitalia:agents:figma-maestro`
- **Impacto ao Usuário (P02):** Prepara a infraestrutura e o catálogo do kit para a chegada do time autônomo sem introduzir agentes fantasma quebrados, permitindo que o desenvolvedor visualize todas as capacidades planejadas do ecossistema.
- **Conformidade Constitucional (P00-P17):** Ferramenta interna de desenvolvimento de software do repositório local. Não processa dados clínicos, biomarcadores ou dados pessoais identificáveis (P07 e P09 não aplicáveis). Auditabilidade técnica e linhagem asseguradas (P14 e P17). Nenhum princípio da rubrica é violado.
- **Referência Arquitetural (ADR):** [ADR-005: Catálogo com Status Operacional e Ingestão AI-Control](file:///home/andre/projetos/assistidos/kit_src/docs/adr/ADR-005-catalogo-com-status-operacional-active-planned.md) e [ADR-006: Instalador Idempotente e Poda de Tokens no Guardian](file:///home/andre/projetos/assistidos/kit_src/docs/adr/ADR-006-instalador-idempotente-e-poda-de-tokens.md).

### FR-010: Correção Idempotente de Nomenclatura no Instalador de Projeto (`source/bin/install-project`)
- **Descrição:** O script `source/bin/install-project` atua como o instalador em nível de repositório consumidor (responsável por vincular o projeto ao kit global `~/.vitalia`, gerando `.agents/AGENTS.md` e os atalhos de skill `.agents/skills/*/SKILL.md` para as IDEs de IA), em contraste com o `kit-bootstrap.sh` que instala o kit global em `~/.vitalia`. Durante a geração dos diretórios de skill em `.agents/skills/`, o instalador **MUST** aplicar a regra determinística de transformação de nomes: se o nome base do arquivo `.toml` iniciar com o prefixo `vitalia-`, esse prefixo deve ser removido via expressão regular `^vitalia-` (`clean_name=$(echo "${ext_name}" | sed 's/^vitalia-//')`), derivando o nome final da skill obrigatoriamente através da interpolação `skill_name="vitalia-${clean_name}"`. Isso garante que a saída seja sempre idempotente, mantenha a integridade dos links dos templates `SKILL.md` e nunca produza duplicações como `vitalia-vitalia-*`.
- **Impacto ao Usuário (P02):** Elimina a geração de comandos espúrios como `/vitalia-vitalia-route` e `/vitalia-vitalia-integrative-review`, garantindo que os atalhos de skill em `.agents/skills/` reflitam com precisão os comandos canônicos `/vitalia-route` e `/vitalia-integrative-review`.
- **Conformidade Constitucional (P00-P17):** Ferramenta interna de desenvolvimento de software do repositório local. Não processa dados clínicos, biomarcadores ou dados pessoais identificáveis (P07 e P09 não aplicáveis). Auditabilidade técnica e linhagem asseguradas (P14 e P17). Nenhum princípio da rubrica é violado.
- **Referência Arquitetural (ADR):** [ADR-006: Instalador Idempotente e Poda de Tokens no Guardian](file:///home/andre/projetos/assistidos/kit_src/docs/adr/ADR-006-instalador-idempotente-e-poda-de-tokens.md).

### FR-011: Equalização de Contexto e Poda Semântica de Tokens nos Adaptadores do Guardian
- **Descrição:** Os adaptadores `RoutingTableAdapter`, `AgentsCatalogAdapter` e `BrainstormingIntentsAdapter` em `source/src/hooks/guardian_context.py` **MUST** implementar o subsistema de equalização proporcional de contexto (`source_weights`), respeitando a cota calculada `src_token_limit` em função do `hardware_profile`: aplicando limite estrito de até 1000 tokens por adaptador para perfis `lightweight` locais (prevenindo sobrecarga de tokens no Qwen2.5 3B) e orçamento expandido de até 4000 tokens para o perfil `frontier` na IDE. A poda deve ser semântica, filtrando entidades com `status: planned` quando a cota for restrita.
- **Impacto ao Usuário (P02):** Acelera a inferência do LLM local em execuções de gates sem truncar nem asfixiar a janela de contexto de modelos de fronteira na IDE, preservando foco e clareza.
- **Conformidade Constitucional (P00-P17):** Ferramenta interna de desenvolvimento de software do repositório local. Não processa dados clínicos, biomarcadores ou dados pessoais identificáveis (P07 e P09 não aplicáveis). Auditabilidade técnica e linhagem asseguradas (P14 e P17). Nenhum princípio da rubrica é violado.
- **Referência Arquitetural (ADR):** [ADR-006: Instalador Idempotente e Poda de Tokens no Guardian](file:///home/andre/projetos/assistidos/kit_src/docs/adr/ADR-006-instalador-idempotente-e-poda-de-tokens.md).

---

## 3. Requisitos Não-Funcionais (Restrições Técnicas)

- **RNF-001 (Isolamento de Dados Local - P07):** Nenhuma operação de escrita de handoff pode ocorrer fora do diretório local do projeto em `.vitalia/memory/data_storage/handoffs/`. Diretórios de sistema como `/tmp` e `~/.vitalia/tmp` são expressamente vedados para payloads de handoff.
- **RNF-002 (Autonomia sem Redis - P11):** Todo o mecanismo de roteamento, criação, validação e consumo de handoffs deve operar 100% via sistema de arquivos local e Python standard/jsonschema, sem requerer daemon do Redis em execução.
- **RNF-003 (Latência de Validação Pré-Hook - P14):** O tempo total de leitura e validação estrutural do arquivo de handoff via `jsonschema.validate()` **MUST** ser inferior a 100ms no percentil 95 (p95), medido em suíte de testes de benchmark automatizada (`pytest`) em hardware de referência padrão (CPU x86_64).
- **RNF-004 (Aderência Constitucional Holística):** A especificação adere integralmente aos princípios constitucionais invioláveis: P00 (*Human Wellbeing First*), P01 (*SDD Pipeline*), P02 (*User-Centric Validation*), P04 (*Timestamp GMT-04:00*), P07 (*Privacy by Design*), P09 (*Medical Safety Gate - Isenção declarada*), P11 (*Hardware-Agnostic Routing*), P12 (*Agent Security & Schema Validation*), P14 (*Fail-safe Traceability*) e P17 (*EU AI Act Compliance*).

---

## 4. Histórias de Usuário (User Stories)

### US1: Transição Fluida e Determinística entre Concepção e Roteamento
**Como um** desenvolvedor participando de um ciclo de ideação no `/vitalia-brainstorming`,  
**eu quero** que o consenso técnico seja gravado automaticamente em um artefato estruturado e transferido para o `/vitalia-route`,  
**para que** eu não precise redigitar argumentos ou sofrer perda de contexto ao avançar para a especificação formal.

### US2: Escalação Segura quando Agentes Especialistas Extrapolam Domínio
**Como um** desenvolvedor interagindo com um agente especialista de implementação (ex: `Django-Stark`),  
**eu quero** que qualquer proposta de nova regra de negócio gere um handoff formal de retorno ao Brainstorming,  
**para que** a integridade da arquitetura seja preservada e nenhuma decisão técnica ocorra sem governança prévia.

### US3: Catálogo Íntegro e Nomenclatura Padronizada de Comandos
**Como um** Tech Lead utilizando o Vitalia Kit,  
**eu quero** que todos os comandos instalados tenham nomes canônicos (sem duplicações como `vitalia-vitalia-*`) e que o catálogo distinga com clareza o que é executável hoje do que está planejado,  
**para que** o time opere com previsibilidade e sem comandos fantasmas quebrados.

---

## 5. Critérios de Aceite (Acceptance Scenarios)

### Cenário 1: Geração de Handoff Estruturado pelo Brainstorming
- **Dado que** o usuário concluiu uma rodada de brainstorming e autorizou o avanço,
- **Quando** o processo de handoff for executado,
- **Então** um arquivo `handoff_brainstorming_to_vitalia-route_<uuid_8>.json` deve ser criado em `.vitalia/memory/data_storage/handoffs/`,
- **E** o arquivo deve conter `schema_type: "workflow_handoff"`, `schema_version: "1.0.0"`, `envelope.direction: "forward"`, `envelope.status: "pending"` e o identificador de máquina resolvido,
- **E** o usuário deve receber a instrução de acionar `/vitalia-route --handoff=<id>`.

### Cenário 2: Bloqueio de Payload Inválido na Validação Pré-Hook (P12/P14)
- **Dado que** existe um arquivo de handoff em `data_storage/handoffs/` com campo obrigatório ausente (ex: sem `envelope.direction` ou sem `envelope.handoff_id`),
- **Quando** o comando de destino for invocado com `--handoff=<id>`,
- **Então** o script pré-hook de validação deve emitir código de erro 1,
- **E** a execução do workflow deve ser interrompida antes que qualquer contexto corrompido atinja o LLM.

### Cenário 3: Consumo e Despacho de Especialistas pelo `vitalia-route`
- **Dado que** um handoff válido com `intent_type: "brainstorming_to_route"` e `envelope.direction: "forward"` está pendente em `data_storage/handoffs/`,
- **Quando** o desenvolvedor executar `/vitalia-route --handoff=<id>`,
- **Então** o `guardian_json.session_context.handoff` deve conter os dados estruturados do handoff,
- **E** o status do arquivo no disco deve ser atualizado atomicamente para `"consumed"`,
- **E** o `vitalia-route` deve propor o Especialista do Catálogo adequado para a fase (ex: `/vitalia-design-thinking` para descoberta/PRD), reservando `/vitalia-spec-specify` para quando a concepção estiver madura.

### Cenário 4: Disparo do Fluxo Invertido de Escalação
- **Dado que** um agente de execução (ex: `spec-implement`) identifica uma divergência arquitetural ou expansão de escopo não autorizada,
- **Quando** o agente acionar o protocolo de escalação invertida,
- **Então** um arquivo `divergence_<uuid_8>.json` deve ser salvo em `data_storage/handoffs/`,
- **E** um arquivo de handoff `handoff_spec-implement_to_vitalia-route_<uuid_8>.json` com `envelope.direction: "reverse"` e `intent_type: "route_to_brainstorming"` deve ser persistido em `data_storage/handoffs/`,
- **E** o desenvolvedor deve ser orientado a retornar ao `/vitalia-route` ou `/vitalia-brainstorming` com o ID gerado para repactuação soberana HITL.

### Cenário 5: Instalação Idempotente sem Duplicação de Prefixos
- **Dado que** os arquivos de extensão em `source/extensions/` incluem `vitalia-route.toml` e `vitalia-integrative-review.toml`,
- **Quando** o script `install-project` for executado,
- **Então** os diretórios de skill gerados em `.agents/skills/` devem ser estritamente `vitalia-route/` e `vitalia-integrative-review/`,
- **E** nenhum diretório ou comando `vitalia-vitalia-*` deve ser criado.

### Cenário 6: Separação de Status no `agents_catalog.yaml`
- **Dado que** o arquivo `agents_catalog.yaml` é carregado pelo Guardian,
- **Quando** o adaptador processar o catálogo,
- **Então** os 6 agentes do AI-Control e os 4 agentes legados sem TOML devem apresentar `status: "planned"`,
- **E** apenas agentes com arquivos `.toml` executáveis ativos devem apresentar `status: "active"`.

---

## 6. Suposições Verificadas (Grounding P03)

- **"LangGraph Supervisor & Swarm Pattern":** Verificado em https://github.com/langchain-ai/langgraph-supervisor-py e documentação oficial de multi-agentes em 16-10-2026.
- **"OpenAI Agents SDK / Handoff Primitives":** Verificado na arquitetura de handoffs nativos vs agents-as-tools em 16-10-2026.
- **"Claude Code / Antigravity Subagents Architecture":** Verificado nos padrões de context window economics e isolamento de tarefas ruidosas em 16-10-2026.
- **"OWASP Top 10 for LLMs 2025 (LLM01 / LLM07)":** Verificado em https://owasp.org/www-project-top-10-for-large-language-model-applications em 16-10-2026.
- **"jsonschema Python Library":** Verificado no PyPI (suporte a Draft-07 RFC e validação estrita de schemas JSON) em 16-10-2026.

---

## 7. Fora do Escopo (Out of Scope)

- Implementação de conexões e consumidores assíncronos baseados em Redis Streams (`vitalia:handoffs`, `vitalia:events`).
- Criação dos arquivos `.toml` e prompts executáveis dos 6 agentes da equipe AI-Control (serão implementados em ciclo subsequente dedicado).
- Migração global de todo o kit para o diretório `data_storage` (já mapeada para turno futuro de infraestrutura).
