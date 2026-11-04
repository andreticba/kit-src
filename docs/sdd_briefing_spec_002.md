# SDD Briefing Canônico — Spec 002: Universal Bootstrap & Runtime (Vitalia SPEC Kit v0.0.1)

> <!-- sdd_briefing_spec_002.md | Vitalia SPEC Kit v0.0.1 | 03-11-2026 20:00:00(GMT-04:00) -->
> **sdd_briefing_spec_002.md | Vitalia SPEC Kit v0.0.1 | 03-11-2026 20:00:00(GMT-04:00)**

---

## 1. Sumário Executivo e Propósito do Documento

Este briefing estabelece as diretrizes canônicas, arquiteturais e contratuais para o desenvolvimento da **Spec 002: Universal Bootstrap & Runtime** no repositório **Vitalia SPEC Kit (v0.0.1)**. 

O objetivo da Spec 002 é transformar o kit em um produto **100% autônomo, distribuível e instalável via `git clone` em qualquer máquina limpa**, eliminando qualquer dependência do kit legado, de containers Docker locais (Ollama, Redis, Postgres), de podas artificiais de contexto de 6 GB de VRAM e de caminhos absolutos hardcoded.

Este documento consolida:
1. **O Rastro de Pesquisa de 2026** (padrões da Anthropic para Managed Agents, isolamento de runtime e ISO 29148);
2. **Todos os Pivôs Críticos** acordados durante os turnos de alinhamento arquitetural;
3. **A Análise Exaustiva e Contratos Formais dos 11 Arquivos `.toml`** do ciclo SDD e governança;
4. **A Regência do `vitalia-architect` (Arquiteto de Soluções e Tech Lead Sênior)** sobre a condução do pipeline SDD;
5. **A Infraestrutura da Memória 3-Tier com partição por `machine_id`** e o novo repouso do Context Lifting em `.vitalia/memory/data_storage/context/`;
6. **A Nova Ordem de Instruções em `AGENTS.md`** contra a diluição de contexto (*Lost in the Middle*).

---

## 2. Rastro de Pesquisa e Grounding do Estado da Arte (2026)

Em conformidade com o princípio constitucional **P03 (External Verification Protocol)**, toda decisão técnica abaixo é ancorada em literatura e documentação oficial verificada de 2026:

| # | Fonte Canônica | URL Verificada | Data | Princípio Técnico de 2026 Incorporado |
|---|---|---|---|---|
| **E1** | **Anthropic Engineering (Abril 2026)** — *Scaling Managed Agents: Decoupling the brain from the hands* | [`https://www.anthropic.com/engineering/managed-agents`](https://www.anthropic.com/engineering/managed-agents) | 03-11-2026 | **Decouple Brain from Hands & Session:** O harness do LLM (Brain) é *stateless* e descartável (*cattle*). As ferramentas/sandboxes (Hands) operam de forma isolada. O log de eventos (Session) é durável e reside fora da janela de contexto (*"The session is not the context window"*). |
| **E2** | **Anthropic Platform Docs (2026)** — *Claude Managed Agents Overview* | [`https://platform.claude.com/docs/en/managed-agents/overview`](https://platform.claude.com/docs/en/managed-agents/overview) | 03-11-2026 | **Context Interrogation & Positional Slices:** O modelo interroga o histórico sob demanda via fatias posicionais e *Prompt Caching*, em vez de manter históricos monolíticos estáticos. |
| **E3** | **LMSYS / UC Berkeley** — *Judging LLM-as-a-Judge with MT-Bench & Chatbot Arena* | [`https://arxiv.org/abs/2306.05685`](https://arxiv.org/abs/2306.05685) | 03-11-2026 | **Inverted Chain-of-Thought (Critique-First, Verdict-Last):** Proibição de veredito antecipado em avaliações constitucionais para mitigar viés de posição e auto-afirmação. Subsidia o Sub-Agente `/vitalia-judge`. |
| **E4** | **PyPA** — *pipx: Isolated Python Application Environments* | [`https://github.com/pypa/pipx`](https://github.com/pypa/pipx) | 03-11-2026 | **Runtime Isolation:** O kit mantém seu próprio interpretador e bibliotecas em `~/.vitalia-spec-kit/.venv/`, expondo shims para o usuário sem interferir no projeto host. |
| **E5** | **ISO/IEC/IEEE 29148:2018** — *Systems and Software Engineering: Requirements Engineering* | [`https://www.iso.org/standard/72089.html`](https://www.iso.org/standard/72089.html) | 03-11-2026 | **Critérios Canônicos de Requisitos:** Requisitos individuais devem ser estritamente *Unambiguous* (interpretação única), *Measurable* (quantificáveis) e *Singular* (sem conjunções ocultas). Embaseia o checklist de qualidade do `spec-specify.toml`. |

---

## 3. Registro dos Pivôs Críticos da Arquitetura

Durante o processo de refinamento, foram acordados 8 pivôs estratégicos em relação ao kit legado:

### Pivô 1: Descontinuação da Poda de Contexto de 6 GB VRAM
* **Estado Anterior:** Perfis `gp_*.yaml` impunham tetos artificiais (ex.: `total_budget = min(total_budget, 1000)` para perfil lightweight) para viabilizar inferência em GPUs modestas (GTX 1060 de 6 GB) via Ollama local. Isso mutilava a Constituição de 3.000 tokens e provocava amnésia decisória.
* **Decisão:** No Vitalia SPEC Kit, a inferência opera diretamente na IDE Antigravity com **modelos de fronteira**. O Guardian (§11) agora injeta a **Constituição integral sem cortes ou truncamentos**.

### Pivô 2: Saneamento da Infraestrutura Conteinerizada
* **Estado Anterior:** O `scan_environment.py` e o `kit_env_bootstrap.py` executavam probes de socket TCP nas portas `6379` (Redis) e `5432` (Postgres), disparavam `docker compose up -d vitalia_redis` e geravam status `DEGRADED` se os containers não estivessem ativos.
* **Decisão:** Toda dependência de containers locais foi abandonada. O kit opera no filesystem puro. O `scan_environment.py` passa a verificar estritamente: (a) Presença do `.env` local do projeto; (b) Presença de `.agents/AGENTS.md` e `.agents/skills/`; (c) Integridade do runtime em `~/.vitalia-spec-kit/.venv/`.

### Pivô 3: Destino do Context Lifting na Memória 3-Tier
* **Estado Anterior:** Os arquivos de contexto gerados pelo hook runner e pelo Guardian eram despejados na pasta global `~/.vitalia/tmp/`.
* **Decisão:** Para cumprir o princípio **P07 (Zero Data Leak)** e respeitar o isolamento por projeto e por máquina, os arquivos de Context Lifting são gerados dentro do repositório transitório do projeto:
  ```
  .vitalia/memory/data_storage/context/<workflow>_<session_id>_<machine_id>_<pid_hash>.json
  ```

### Pivô 4: Silêncio Arquitetural sobre o CLI Legado `sdd_judge.py`
* **Estado Anterior:** Instruções negativas no `AGENTS.md` avisavam o modelo: *"Não execute sdd_judge.py no terminal"*.
* **Decisão:** O código de `sdd_judge.py` **não foi e não será portado** para o novo produto. Ele não existe no repositório. Em vez de regras negativas defensivas, o nome `sdd_judge.py` foi completamente purgado. O único mecanismo oficial de julgamento é o Sub-Agente nativo da IDE **/vitalia-judge**.

### Pivô 5: Papel do Brainstorming vs. Architect
* **Estado Anterior:** O `brainstorming.toml` era apontado como o início compulsório do SDD, tentando cobrir simultaneamente ideação e início da spec formal.
* **Decisão:** 
  * O **`/vitalia-brainstorming`** é o espaço aberto de ideação socrática (concepção ampla em turnos de até 3 perguntas, cobrindo saúde, produto, didática e pesquisa).
  * O **`/vitalia-route`** atua como despachante semântico.
  * O **`/vitalia-architect` (Arquiteto de Soluções e Tech Lead Sênior)** é o agente de engenharia que recebe os consensos do Brainstorming, avalia trade-offs, cria ADRs e aciona formalmente o ciclo SDD via `/vitalia-spec-specify`.

### Pivô 6: Estratégia Bifurcada de Testes em `spec-tasks` (P05)
* **Estado Anterior:** TDD impunha que toda tarefa exigia teste falhando antes (Red Phase), o que criava um impasse em correções de defeitos onde o código existente já passava nos testes antigos.
* **Decisão:** A Constituição (P05) e o `spec-tasks.toml` bifurcam a estratégia:
  * *Código Novo:* TDD clássico (Red phase comprovando ausência da funcionalidade antes do código).
  * *Bugfix / Correção:* **Bug Reproduction Test First** (escrever um teste específico de regressão que reproduz o defeito e falha no código atual, tornando-se verde após a correção).
  * *Refatoração:* **Golden Master / Characterization Tests** (garantir cobertura da suite existente e aprovação verde antes e depois de alterações estruturais).

### Pivô 7: Foco da Spec 002 vs. Spec 003
* **Decisão:** A Spec 002 foca exclusivamente nas **fundações de runtime e governança**: instalador universal, isolamento de venv, saneamento dos 11 TOMLs base, consolidação do `vitalia-architect` e Context Lifting seguro. A ativação executável do esquadrão de 5 especialistas (`Django-Stark`, `React-Vinci`, `Infra-Nomad`, `Cortex-Analyst`, `Figma-Maestro`) é alocada para a **Spec 003**, evitando inchaço desordenado de escopo.

### Pivô 8: Diagramas Mermaid em Tema Nativo
* **Decisão:** Proibição de classes CSS customizadas (`fill:#...`, `stroke:#...`) nos diagramas Mermaid, que causavam perda de contraste com as fontes da IDE. Os diagramas devem usar Mermaid puro para herdar a paleta nativa da IDE com contraste garantido.

---

## 4. Análise Individual e Contratos dos 12 Arquivos `.toml` em `source/extensions/`

Para cada arquivo TOML do novo produto, definem-se os contratos de entrada, execução e aceite, incorporando as diretrizes de 2026:

### 1. `session-start.toml`
* **Perspectiva do LLM:** Lê `.vitalia/memory/session/` (repo compartilhado). Apresenta a feature ativa, semáforo de sincronização e o próximo passo P0.
* **Recursos:** Ferramentas `run_command` e `read_file`.
* **Contrato de Aceite (ACs):**
  * `AC-START-01`: Remover `hardware_profile = "lightweight"` em favor de `"frontier"`.
  * `AC-START-02`: Definir `preferred = "filesystem"` no transporte (purgar menções a Redis).
  * `AC-START-03`: Executar `git -C .vitalia/memory/session pull --rebase` para sincronizar o contexto compartilhado da equipe. Se a pasta não existir, inicializar via `context_engine.py --action init` de forma resiliente.
  * `AC-START-04`: Interrogar o log posicional da sessão (`SESSION_STATE.md` e `LEARNINGS.md`) sem carregar históricos mortos.

### 2. `spec-specify.toml`
* **Perspectiva do LLM:** Consome `specs/*/research-brainstorming.md` (quando disponível) e o input do usuário. Produz a especificação técnica agnóstica de tecnologia em `spec.md` e valida via checklist ISO 29148.
* **Recursos:** `read_file`, `write_file`, `list_dir`.
* **Contrato de Aceite (ACs):**
  * `AC-SPEC-01`: Incluir `specs/*/research-brainstorming.md` na chave `[context] reads`.
  * `AC-SPEC-02`: Requisitos funcionais (FR-xxx) estruturados sem detalhes prematuros de implementação (linguagens, libs, APIs).
  * `AC-SPEC-03`: Seção obrigatória `## Suposições Verificadas` contendo links externos com HTTP 200 comprovado (P03).
  * `AC-SPEC-04`: Disparo compulsório do Sub-Agente `/vitalia-judge --mode=specify` com pausa soberana para aprovação humana (HITL).

### 3. `judge.toml` (Sub-Agente Constitucional Adversarial)
* **Perspectiva do LLM:** Auditor Red Team. Lê o artefato da fase sob inspeção e o confronta com a totalidade da Constituição (P00 a P18).
* **Recursos:** `read_file`, `write_file`, `grep_search`.
* **Contrato de Aceite (ACs):**
  * `AC-JUDGE-01`: Ingestão da Constituição integral via Guardian sem podas de token budget.
  * `AC-JUDGE-02`: Aplicação estrita de *Inverted Chain-of-Thought (E3)*: extração literal de evidências com número de linha → análise crítica individual contra os princípios → emissão do veredito `PASS`, `WARN` ou `BLOCK` por último.
  * `AC-JUDGE-03`: Emissão obrigatória do artefato físico `specs/{FEATURE}/Relatório de Inspeção - {mode}.md`.
  * `AC-JUDGE-04`: Silêncio total sobre CLIs legados; a auditoria é 100% nativa na IDE.

### 4. `spec-plan.toml`
* **Perspectiva do LLM:** Lê `spec.md` aprovada. Desenha arquitetura técnica, modelo de dados e contratos de interface.
* **Recursos:** `read_file`, `write_file`, `web_search`.
* **Contrato de Aceite (ACs):**
  * `AC-PLAN-01`: Esquemas em `contracts/` estritamente compatíveis com OpenAPI 3.0 puro (proibidos `$schema`, `title` raiz e `additionalProperties: false`).
  * `AC-PLAN-02`: Documentação explícita de trade-offs técnicos e matriz de compatibilidade de dependências externas.
  * `AC-PLAN-03`: Submissão mandatória à auditoria `/vitalia-judge --mode=plan`.

### 5. `spec-tasks.toml`
* **Perspectiva do LLM:** Converte `plan.md` em tarefas atômicas sequenciais (`T001 [P] [US1]`), definindo arquivos exatos e estratégia de testes contextual.
* **Recursos:** `read_file`, `write_file`.
* **Contrato de Aceite (ACs):**
  * `AC-TASKS-01`: Aplicar a estratégia bifurcada de testes (P05): TDD Red Phase para código novo; Bug Reproduction Test First para correções de defeito; Characterization Tests para refatoração.
  * `AC-TASKS-02`: Rastreabilidade explícita: cada tarefa mapeia para uma User Story (`[US1]`).
  * `AC-TASKS-03`: Submissão mandatória à auditoria `/vitalia-judge --mode=tasks`.

### 6. `spec-implement.toml`
* **Perspectiva do LLM:** Executa o `tasks.md` tarefa por tarefa. Escreve testes, implementa código, roda linter, atualiza `[ ]` para `[X]`.
* **Recursos:** `read_file`, `write_file`, `replace_file_content`, `run_command`.
* **Contrato de Aceite (ACs):**
  * `AC-IMPL-01`: Proibição absoluta de marcar `[X]` sem aprovação comprovada da suite de testes correspondente.
  * `AC-IMPL-02`: Preservação compulsória de cabeçalhos P04 e docstrings existentes.
  * `AC-IMPL-03`: Operação com Context Lifting: o payload de contexto é consumido de `.vitalia/memory/data_storage/context/`.

### 7. `converge.toml`
* **Perspectiva do LLM:** Auditoria de convergência quadridimensional entre código real implementado e artefatos SDD (`spec`, `plan`, `tasks`).
* **Recursos:** `read_file`, `list_dir`, `grep_search`, `write_file`.
* **Contrato de Aceite (ACs):**
  * `AC-CONV-01`: Reversão de status no `tasks.md` para qualquer tarefa falsamente marcada como `[X]` que contenha stubs vazios (`pass`) ou mocks não-funcionais.
  * `AC-CONV-02`: Disparo do Sub-Agente `/vitalia-judge --mode=converge` nativo na IDE.

### 8. `session-end.toml`
* **Perspectiva do LLM:** Conduz a reflexão cognitiva de fim de ciclo em 4 fases, registrando aprendizados e decisões no Repositório de Contexto Compartilhado.
* **Recursos:** `read_file`, `write_file`, `run_command`.
* **Contrato de Aceite (ACs):**
  * `AC-END-01`: Gravação estruturada em `.vitalia/memory/session/data/learnings.jsonl` e `decisions.jsonl` contendo obrigatoriamente o `machine_id` da estação local.
  * `AC-END-02`: Commit no repositório git local de contexto, tolerante a offline e sem push bloqueante.

### 9. `session-consolidate.toml`
* **Perspectiva do LLM:** Recompila o dashboard visual `README.md` da sessão e consolida os shards multi-máquina.
* **Recursos:** `read_file`, `run_command`, `write_file`.
* **Contrato de Aceite (ACs):**
  * `AC-CONS-01`: Deduplicação determinística de shards em `.vitalia/memory/session/shards/<machine_id>.yaml` preservando o timestamp `last_sync` mais recente.
  * `AC-CONS-02`: Compilação de visões puras (`SESSION_STATE.md`, `LEARNINGS.md`, `DECISIONS.md`) operando no filesystem local.

### 10. `brainstorming.toml`
* **Perspectiva do LLM:** Facilitador Socrático Amplo (Design Thinking e Concepção).
* **Recursos:** `read_file`, `write_file`.
* **Contrato de Aceite (ACs):**
  * `AC-BRAIN-01`: Protocolo estrito STOP → SCAN → ASK → WAIT.
  * `AC-BRAIN-02`: Formulação de **no máximo 3 perguntas por turno**, priorizando decisões P0 (saúde, privacidade e segurança) quando detectadas.
  * `AC-BRAIN-03`: Ativação do Scope Guardian para conter o MVP e alocar expansões em `🚧 Ideias Estacionadas (Out of Scope)`.
  * `AC-BRAIN-04`: **Loop Contínuo com Soberania HITL:** Novos turnos de até 3 perguntas são iniciados enquanto restarem dúvidas, encerrando-se **apenas** quando o usuário concordar explicitamente que a concepção está madura.
  * `AC-BRAIN-05`: Emissão de `specs/<feature>/research-brainstorming.md` e disparo do handoff `forward` exclusivamente para o `/vitalia-route`.

### 11. `route.toml`
* **Perspectiva do LLM:** Despachante Oficial do Kit. Lê o handoff do Brainstorming e direciona o fluxo para o especialista adequado do catálogo.
* **Recursos:** `read_file`.
* **Contrato de Aceite (ACs):**
  * `AC-ROUTE-01`: Consulta determinística da tríade de arquivos: `brainstorming_intents.yaml` (domínio) → `agents_catalog.yaml` (`target_agent`) → `routing_table.yaml` (`command`).
  * `AC-ROUTE-02`: Encaminhamento obrigatório de demandas de software para o **/vitalia-architect** (Arquiteto de Soluções e Tech Lead Sênior).
  * `AC-ROUTE-03`: Confirmação transparente com o usuário antes de efetivar o handoff.

### 12. `architect.toml` — O Condutor Oficial do Ciclo SDD (Vitalia Architect)
* **Perspectiva do LLM:** Você é o **Vitalia Architect**, Arquiteto de Soluções e Tech Lead Sênior. Você é o condutor oficial e soberano do ciclo SDD. Você recebe o bastão do `/vitalia-route` (trazendo o `research-brainstorming.md`), avalia trade-offs de engenharia, isolamento de dados, conformidade e impacto arquitetural, cria ADRs quando necessário e aciona formalmente o início do pipeline SDD disparando o `/vitalia-spec-specify`.
* **Recursos:** `read_file`, `write_file`.
* **Contrato de Aceite (ACs):**
  * `AC-ARCH-01`: Ingestão do artefato `specs/<feature>/research-brainstorming.md` encaminhado pelo `route`.
  * `AC-ARCH-02`: **Ingestão e Validação Holística da Constituição:** O agente é instruído a inspecionar integralmente o bloco `constitution` injetado no contexto pelo Guardian, validando a solução proposta contra **todos os princípios ativos**, sem enumerações estáticas ou hardcoded no prompt.
  * `AC-ARCH-03`: Registro automático de Architecture Decision Record (`docs/adr/ADR-xxxx-<slug>.md`) sempre que houver escolha estruturante, introdução de nova biblioteca ou mudança de protocolo de persistência/comunicação.
  * `AC-ARCH-04`: Handoff formal e determinístico para `/vitalia-spec-specify`, entregando o briefing consolidado para formalização de requisitos (FRs/SCs).
  * `AC-ARCH-05`: **Contrato TOML Canônico:**
    ```toml
    # architect.toml | Vitalia SPEC Kit v0.0.1
    description = "Arquiteto de Soluções e Tech Lead Sênior (Vitalia Architect). Avalia arquitetura contra a Constituição, cria ADRs e conduz o início do SDD."

    [meta]
    version = "0.0.1"
    hardware_profile = "frontier"
    domain_gates = []

    [hooks]
    before = ["python3 {{VITALIA_KIT_DIR}}/src/hooks/scan_environment.py"]
    after  = []

    [tools]
    required = ["read_file", "write_file"]
    optional = ["run_command"]

    [context]
    reads = [
      "session_context",
      "env_summary",
      "context_learnings",
      "context_decisions",
      "routing_table",
      "agents_catalog",
    ]
    writes = ["active_spec", "adr"]

    [transport]
    file_path     = ".vitalia/pipeline.json"
    session_shard = true

    [guardian]
    yaml_sources = ["constitution", "routing_table", "agents_catalog"]
    guardian_profile = "gp_vitalia-architect"

    prompt = \"\"\"
    ## 🏛️ Identidade — Vitalia Architect (Arquiteto de Soluções e Tech Lead Sênior)

    Você é o **Vitalia Architect**, Arquiteto de Soluções e Tech Lead Sênior do Kit Vitalia.
    Você é pragmático, focado em excelência técnica, contratos explícitos e segurança sistêmica.
    Você é o guardião da integridade arquitetural e o condutor da transição entre a ideação e a execução formal no pipeline SDD.

    ---

    ## Sua Lei Fundamental: A Constituição Injetada

    Sua primeira e mais crítica ação operacional é:
    **Leia integralmente as regras constitucionais presentes no campo `constitution` do seu contexto (`guardian_json`).**
    A Constituição é viva, dinâmica e soberana. Qualquer regra, limitação de arquitetura, política de testes, privacidade ou diretriz de contratos nela definida é de cumprimento obrigatório e tem precedência sobre qualquer premissa ad-hoc.

    ---

    ## Sua Missão

    Você recebe o bastão do `/vitalia-route` contendo o resumo e os consensos validados no `research-brainstorming.md`.
    Sua responsabilidade é transformar essa visão em uma fundação técnica robusta antes de qualquer código ser escrito:

    1. **Auditoria de Conformidade Constitucional:** 
       Confronte a solução concebida no Brainstorming contra cada princípio da Constituição ativa. Se identificar conflitos com políticas de isolamento, contratos, dependências ou governança, ajuste o direcionamento técnico antes de avançar.
    2. **Decisão Arquitetural (ADR):** 
       Se a demanda exigir escolha técnica estruturante (ex: adoção de biblioteca, formato de persistência, modelo de concorrência ou divisão de módulos), registre ou atualize o ADR correspondente em `docs/adr/ADR-xxxx-<slug>.md`.
    3. **Enquadramento da Estratégia de Testes:** 
       Identifique na Constituição a política de testes aplicável à natureza desta demanda (novo código, correção/bugfix ou refatoração) e defina formalmente como a suite de testes guiará o desenvolvimento.
    4. **Condução e Handoff para o SDD:** 
       Estabeleça o diretório da feature em `specs/<feature>/`, aponte `.vitalia/feature.json` e apresente a proposta ao usuário com o comando formal de especificação:
       `-> Proponho avançar para o pipeline SDD formal via: /vitalia-spec-specify`

    ---

    ## Checklist de Avaliação Pré-SDD (Inviolável)

    Antes de recomendar `/vitalia-spec-specify`, confirme categoricamente:
    - [ ] A Constituição injetada no contexto foi lida integralmente e nenhuma diretriz ativa é violada?
    - [ ] Os limites de escopo (o que NÃO será feito) estão explicitamente delimitados?
    - [ ] Todas as dependências externas e interfaces de dados estão alinhadas com os padrões contratuais vigentes?
    - [ ] A estratégia de testes mandatada pela Constituição para este tipo de demanda foi devidamente classificada?
    \"\"\"
    ```

---

## 5. Estrutura Canônica de `brainstorming_intents.yaml`

O catálogo de intenções semânticas é reorganizado para operar como a chave estrangeira determinística do roteamento:

```yaml
# brainstorming_intents.yaml | Vitalia SPEC Kit v0.0.1
schema_type: "brainstorming_intents"
schema_version: "0.0.1"

domains:
  saude_clinica:
    description: "Sistemas médicos, manipulação de PHI/PII, suporte à decisão clínica e privacidade de pacientes."
    target_agent: "medical-gate"
    command: "/vitalia-medical-gate"
    role: "Avaliação de risco clínico e HITL médico"
    threshold: 0.85
    p0_flag: true
    utterances:
      - "Desenvolver módulo de prontuário ou dados de saúde"
      - "Integração com exames laboratoriais ou biomarcadores"
      - "Análise de dados médicos ou diagnósticos"
      - "Tratamento de dados sensíveis de pacientes (LGPD/HIPAA)"
      - "Prescrição ou cálculo de zonas de esforço cardíaco"

  estrategia_produto:
    description: "Concepção de novas funcionalidades, roadmap de produto e descoberta humana."
    target_agent: "design-thinking"
    command: "/vitalia-design-thinking"
    role: "Facilitador de workshops, PRDs e descoberta humana"
    threshold: 0.80
    p0_flag: false
    utterances:
      - "Quero criar uma nova funcionalidade no sistema"
      - "Preciso estruturar a ideia de um novo módulo"
      - "Como podemos desenhar o fluxo de onboarding deste produto?"
      - "Quero fazer um brainstorming de proposta de valor"

  pesquisa_cientifica:
    description: "Revisões sistemáticas, formulação de hipóteses e curadoria de literatura acadêmica indexada."
    target_agent: "literature-curator"
    command: "/vitalia-literature-curator"
    role: "Guardião do acervo e ingestão científica"
    threshold: 0.82
    p0_flag: false
    utterances:
      - "Estruturar protocolo de revisão integrativa com PRISMA"
      - "Levantamento de literatura no PubMed, Scopus ou Web of Science"
      - "Curadoria e fichamento de artigos científicos"

  arquitetura_software:
    description: "Decisões de engenharia de software, modelagem de dados, contratos de API e transição para o pipeline SDD."
    target_agent: "architect"
    command: "/vitalia-architect"
    role: "Transição de consensos para o pipeline SDD formal"
    threshold: 0.80
    p0_flag: false
    utterances:
      - "Como podemos desenhar a arquitetura técnica deste sistema?"
      - "Definir os contratos de interface e modelo de dados"
      - "Documentar uma decisão arquitetural (ADR)"
      - "Estruturar a transição do brainstorming para especificação técnica"
```

---

## 6. Ordem de Instruções no `source/AGENTS.md` (Anti-Lost in the Middle)

Para maximizar a retenção da atenção do modelo de fronteira e assegurar conformidade operacional, a ordem das seções no `source/AGENTS.md` obedece rigorosamente aos princípios de **Primacy Effect** (contextualização inicial rápida) e **Recency Effect** (regras imperativas no final):

```markdown
<!-- AGENTS.md | Vitalia SPEC Kit v0.0.1 | 03-11-2026 20:00:00(GMT-04:00) -->

# AGENTS.md — Vitalia SPEC Kit (v0.0.1)

> [!IMPORTANT]
> **ARQUITETURA v0.0.1 — Runtime Autônomo e Context Lifting Seguro.**
> O Vitalia SPEC Kit opera desacoplado de containers locais. A inferência é conduzida por modelos de fronteira na IDE Antigravity. O Guardian (§11) injeta a Constituição integral sem truncamento de tokens. O contexto de execução reside de forma durável em `.vitalia/memory/data_storage/context/`.

## 1. Topologia do Kit e Localização

```
~/.vitalia-spec-kit/ (Kit Global)            .vitalia/ (Projeto Local)
├── bin/                                     ├── memory/
│   ├── kit-bootstrap.sh                     │   ├── session/      ◄── Repo Compartilhado
│   └── install-project                      │   └── data_storage/ ◄── Repo Transitório
├── extensions/*.toml                        └── feature.json
├── profiles/ (constitution, catalogs)
└── .venv/ (Runtime Python isolado)
```

## 2. Como o Kit Funciona (Context Lifting)

1. Usuário aciona um comando `/vitalia-*` na IDE.
2. A SKILL correspondente invoca `~/.vitalia-spec-kit/.venv/bin/python3 .../vitalia_hook_runner.py`.
3. O hook runner processa o TOML, aciona o Guardian e grava o contexto completo em:
   `.vitalia/memory/data_storage/context/<workflow>_<session>_<machine_id>_<hash>.json`
4. O hook runner emite o Stub JSON no stdout.
5. A IA consome o arquivo referenciado no Stub JSON via ferramenta nativa `view_file`.

## 3. Diretrizes Comportamentais Invioláveis (Zona de Máxima Atenção)

1. **Início e Fim de Sessão:** Toda sessão inicia com `/vitalia-session-start` (sincronizando o Repositório de Contexto Compartilhado via `pull --rebase`) e encerra com `/vitalia-session-end` (registrando aprendizados e decisões com `machine_id`).
2. **Entrada pelo Brainstorming Socrático:** Requisitos novos ou não clarificados passam obrigatoriamente pelo `/vitalia-brainstorming`. O agente formula no máximo 3 perguntas por turno com tabelas de trade-off e encerra o diálogo apenas após confirmação explícita do usuário, gerando `research-brainstorming.md`.
3. **Regência do Architect (Vitalia Architect):** O `/vitalia-route` despacha demandas de engenharia de software para o `/vitalia-architect`. O Architect valida os trade-offs técnicos, registra ADRs quando necessário e dá início ao ciclo SDD acionando o `/vitalia-spec-specify`.
4. **Estratégia de Testes Contextual (P05):**
   * *Código Novo:* TDD estrito com Red Phase confirmada antes do código funcional.
   * *Bugfix / Correção:* Bug Reproduction Test First — escrever teste que falha no código atual antes de aplicar o patch corretivo.
   * *Refatoração:* Golden Master / Characterization Tests garantindo suite verde antes e depois das mudanças.
5. **Auditoria Adversarial Nativa na IDE (/vitalia-judge):** Toda transição de fase (`specify`, `plan`, `tasks`, `converge`) é submetida ao Sub-Agente nativo `/vitalia-judge`. O Juiz aplica *Inverted Chain-of-Thought* (citação literal de linhas → análise crítica contra princípios P00–P18 → veredito PASS/BLOCK por último) e emite o `Relatório de Inspeção` físico.
6. **Soberania HITL e Mínimo Privilégio:** Nenhuma fase do ciclo SDD é promovida sem a aprovação humana expressa do Relatório de Inspeção.
```

---

## 7. Roteiro de Execução da Spec 002 na Janela do Novo Projeto

Para materializar estas definições no repositório `vitalia-spec-kit`, as seguintes tarefas atômicas compõem o plano de implementação da Spec 002:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                         PLANO DE EXECUÇÃO: SPEC 002                                    │
├───────────┬────────────────────────────────────────────────────────────────────────────┤
│ Fase      │ Tarefas Entregáveis                                                        │
├───────────┼────────────────────────────────────────────────────────────────────────────┤
│ Fase 1    │ Topologia & Bootstrap:                                                     │
│ (Setup)   │ - Criar ~/.vitalia-spec-kit/ como destino global unificado.                │
│           │ - Criar kit-bootstrap.sh na raiz, instalando .venv/ com requirements.txt.  │
│           │ - Configurar shims em ~/.local/bin/ apontando para o interpretador isolado.│
├───────────┼────────────────────────────────────────────────────────────────────────────┤
│ Fase 2    │ Desacoplamento de Infraestrutura (Cattle vs. Pets):                        │
│ (Runtime) │ - Reescrever scan_environment.py e kit_env_bootstrap.py: purgar sockets   │
│           │   de Redis (6379), Postgres (5432) e comandos Docker compose.              │
│           │ - Atualizar vitalia_hook_runner.py para direcionar o Context Lifting       │
│           │   para .vitalia/memory/data_storage/context/ com partição por machine_id.  │
│           │ - Purgar telemetria síncrona do Redis Stream em vitalia_hook_runner.py.    │
├───────────┼────────────────────────────────────────────────────────────────────────────┤
│ Fase 3    │ Governança & Constituição:                                                 │
│ (Profiles)│ - Atualizar constitution.yaml: incorporar P18 (Inverted CoT), ajustar P01  │
│           │   (Brainstorming/Architect), P05 (Testes Bifurcados) e P11 (Clean Schemas).│
│           │ - Atualizar brainstorming_intents.yaml com target_agent e command.         │
│           │ - Atualizar source/AGENTS.md com a ordem anti-Lost in the Middle.          │
├───────────┼────────────────────────────────────────────────────────────────────────────┤
│ Fase 4    │ Saneamento e Entrega dos 12 Arquivos .toml:                                │
│ (Ext)     │ - Atualizar session-start, spec-specify, judge, spec-plan, spec-tasks,     │
│           │   spec-implement, converge, session-end, session-consolidate,              │
│           │   brainstorming e route conforme os contratos formalizados na Seção 4.     │
│           │ - Criar architect.toml (Vitalia Architect) conforme contrato AC-ARCH-01/05.│
│           │ - Purgar qualquer menção a sdd_judge.py e hardware_profile = "lightweight".│
├───────────┼────────────────────────────────────────────────────────────────────────────┤
│ Fase 5    │ Validação End-to-End via Dogfooding:                                       │
│ (Quality) │ - Executar kit-bootstrap.sh em diretório limpo.                             │
│           │ - Executar install-project em projeto secundário de teste.                 │
│           │ - Submeter a Spec 002 à auditoria do Sub-Agente /vitalia-judge.            │
└───────────┴────────────────────────────────────────────────────────────────────────────┘
```

---
*Este documento é a especificação formal e completa para iniciar os trabalhos da Spec 002 no repositório vitalia-spec-kit.*
