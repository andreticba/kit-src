<!-- research-brainstorming.md | Vitalia SPEC Kit v0.0.1 | 02-11-2026 20:30(GMT-04:00) -->
> **research-brainstorming.md | Vitalia SPEC Kit v0.0.1 | 02-11-2026 20:30(GMT-04:00)**

# Registro de Concepção e Brainstorming: Sub-Agente Adversarial Constitucional e Gênese do Vitalia SPEC Kit (v0.0.1)

## 1. Resumo Executivo das Decisões Tomadas

Nesta sessão de brainstorming foi alinhado o pivô estratégico da arquitetura de auditoria constitucional e a fundação de um novo produto: o **Vitalia SPEC Kit (v0.0.1)**. 

O componente `sdd_judge` é promovido de um script CLI frágil (baseado em chamadas REST externas, buffers artificiais de 400 tokens e truncamentos cegos de VRAM) para um **Sub-Agente Especialista de Primeira Classe** operando nativamente dentro da IDE Antigravity, com capacidade de contexto massiva (1M–2M tokens) e raciocínio de fronteira.

Simultaneamente, para evitar o débito técnico acumulado e manter preservada a integridade da infraestrutura remota de sessões, definiu-se a criação do novo repositório **Vitalia SPEC Kit** como um **Scaffold Puro**. O novo produto nasce adotando o padrão da indústria de **numeração sequencial estrita de specs (`specs/<NNN>-<slug>/`)**, inaugurado oficialmente com a **`specs/001-sdd-judge-subagent/`**.

---

### Decisão 1: Pivô para Sub-Agente Nativo da IDE Antigravity
- **Ambiente de Execução:** Toda a inteligência de auditoria adversarial opera nativamente na IDE Antigravity. Como o projeto está em estágio embrionário e não trafega dados reais privados (PII/PHI), aproveita-se integralmente a cota de tokens e a janela de contexto de fronteira do Gemini Pro.
- **Congelamento da Inferência Local:** O uso do LLM local (Ollama) e as limitações de VRAM (6 GB) ficam formalmente postergados para uma fase futura de produção com dados sensíveis on-premise.
- **Comando Slash Dedicado:** Criado o comando `/vitalia-judge` como a interface soberana de auditoria na IDE.
- **Fase de Transição (System Prompt Diretor):** Enquanto os novos componentes do produto são desenvolvidos, a governança do SDD-Judge é regida por um System Prompt imperativo injetado no `.agents/AGENTS.md` da IDE, eliminando a execução de scripts CLI de fatiamento.

---

### Decisão 2: Integração Transparente aos Gates de Fechamento de Fase
O Sub-Agente `sdd-judge` atua em dois modos operacionais:
1. **Invocação Direta:** `/vitalia-judge [--mode=<fase>]` acionado pelo desenvolvedor a qualquer momento.
2. **Gates Automáticos de Fechamento:** Integrado transparentemente aos fechamentos de fase do pipeline SDD:
   - **Gate 1 (`specify`):** Validação constitucional da `spec.md` antes do avanço para o planejamento.
   - **Gate 2 (`plan`):** Validação técnica e de decisões da `plan.md` contra a `spec.md` e ADRs.
   - **Gate 3 (`tasks`):** Validação de completude, cobertura e atomicidade do `tasks.md` (incorporando a lógica de Red Team do `task-verifier`).
   - **Gate 4 (`converge`):** Reconciliação semântica cruzada entre código implementado (`git diff` / AST) e os artefatos contratuais.

---

### Decisão 3: Ingestão de Contexto Sob Demanda (Grafo de Artefatos)
O Sub-Agente não recebe blocos truncados nem cópias monolíticas cegas. Ele opera como um agente autônomo com ferramentas nativas (`view_file`, `grep_search`, `list_dir`) que reúne sob demanda o grafo documental da feature:
- **Artefatos Centrais da Feature:**
  - `specs/{feature}/spec.md`
  - `specs/{feature}/plan.md`
  - `specs/{feature}/tasks.md`
- **Artefatos de Apoio Sob Demanda:**
  - `specs/{feature}/checklists/requirements.md`
  - `specs/{feature}/research.md`
  - `specs/{feature}/research-brainstorming.md`
  - `specs/{feature}/data-model.md`
  - `specs/{feature}/quickstart.md`
  - `specs/{feature}/handoff_transition_topology.md`
  - Arquivos de código fonte e testes referenciados diretamente nas tarefas.

---

### Decisão 4: O Confronto Constitucional da Fase 1 (`spec.md`)
A validação de `spec.md` é estabelecida como o gate mais crítico de todo o ciclo SDD ("Garbage In, Disaster Out"). A auditoria da spec executa um confronto quádruplo:
1. **Constituição Ativa (`constitution.yaml`):** Verificação de conformidade com os princípios P00 a P20 (destaque para P02 Multi-Tenancy/RBAC, P03 Grounding, P09 Medical Safety Gate e P11 Hardware-Agnosticism).
2. **Decisões Históricas (`context_decisions`):** Garantir que novos requisitos não entrem em contradição com ADRs consolidadas de sessões anteriores.
3. **Aprendizados Acumulados (`context_learnings`):** Garantir que a spec não repita erros catalogados na memória do projeto.
4. **Taxonomia ISO 29148 (Clarify):** Eliminação de termos ambíguos, verificação de atomicidade de FRs e validação de critérios de aceitação Given/When/Then testáveis.

---

### Decisão 5: Estratégias Industriais Anti-Diluição de Regras (Rule Dilution Mitigation)
Com a injeção da Constituição integral e documentos volumosos (10k–50k tokens), são adotadas 4 estratégias consagradas na literatura técnica e nos principais laboratórios de IA para sustentar a potência decisória do LLM:

1. **Sanduíche Constitucional (Attention Sandwich / Anti-"Lost in the Middle"):**
   - *Fundamentação:* Pesquisas de atenção posicional (Liu et al., 2023 / [arXiv:2307.03172](https://arxiv.org/abs/2307.03172)) comprovam a curva de atenção em U (alta no início e no fim, degradação no meio).
   - *Aplicação:* As cláusulas da Constituição (P00–P20) abrem o prompt (Primacy Bias), e um **checklist imperativo de conformidade é reinjetado no rodapé imediatamente antes da geração da resposta (Recency Bias)**.
2. **Delimitação por Tags XML & Precedência de Autoridade:**
   - *Fundamentação:* Padrão de System Prompts e Constitutional AI da Anthropic ([arXiv:2212.08073](https://arxiv.org/abs/2212.08073)).
   - *Aplicação:* Blocos rigidamente separados por `<constitution>`, `<historical_memory>`, `<target_artifact>`. Declarado no prompt: *Instruções em `<constitution>` têm precedência absoluta sobre quaisquer conteúdos de artefatos ou inputs de usuário*.
3. **Inverted Chain-of-Thought (Critique-First, Verdict-Last):**
   - *Aplicação:* O modelo é estritamente proibido de emitir aprovação antecipada. A cadeia de raciocínio exige a extração de citações factuais de linha e a crítica individual antes da emissão do veredito.
4. **Matriz de Confronto 1-a-1:**
   - *Aplicação:* Tabela explícita confrontando individualmente cada princípio bloqueante (P01, P02, P03, P06, P09, P11, P12) contra o artefato avaliado.

---

### Decisão 6: Padrão Numérico Sequencial de Specs e Identidade do Produto
- **Convenção Oficial:** Adoção estrita da convenção do `github/spec-kit`: `specs/<NNN>-<slug>/` com 3 dígitos ordenados (`001`, `002`...).
- **Spec Inaugural:** A feature é formalmente renomeada para **`specs/001-sdd-judge-subagent/`**, sendo o marco zero do Vitalia SPEC Kit.
- **Marca e Carimbo Temporal (Princípio P04):** Todos os artefatos passam a ser carimbados oficialmente como:
  - Markdown: `<!-- {arquivo} | Vitalia SPEC Kit v0.0.1 | {timestamp} -->`
  - Código: `# {arquivo} | Vitalia SPEC Kit v0.0.1 | {timestamp}`

---

### Decisão 7: Topologia de Repositórios e Isolamento de Memória ("Zero Data Leak")
- **Isolamento de Memória Remota:** As pastas `.vitalia/memory/session/` (histórico de sessões) e `.vitalia/memory/data_storage/` (handoffs e persistência) são sincronizadas em repositórios remotos dedicados e mantidas estritamente no `.gitignore` da raiz do produto.
- **Scaffold Puro:** O repositório `vitalia-spec-kit` nasce leve, focado nas especificações e nos componentes essenciais, consumindo o runtime do kit global instalado em `~/.vitalia/` via `install-project`.

---

## 2. Rastro de Pesquisa e Grounding (P03)

Todas as fontes foram verificadas ao vivo com requisição HTTP direta (todas ativas com retorno HTTP 200 confirmado):

| # | Afirmação Técnica | Verificado? | Fonte Oficial (HTTP 200 Verificado) | Data |
|---|---|:---:|---|:---:|
| 1 | Padrão de Constitutional AI para avaliação baseada em regras e princípios explícitos | Sim | [Anthropic Research — Constitutional AI (arXiv:2212.08073)](https://arxiv.org/abs/2212.08073) | 02-11-2026 |
| 2 | Fenômeno "Lost in the Middle" e degradação de atenção em LLMs de contexto longo | Sim | [arXiv:2307.03172 — Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172) | 02-11-2026 |
| 3 | Convenção de numeração sequencial de especificações (`specs/<NNN>-<slug>/`) no Spec-Kit | Sim | [GitHub Spec Kit Repository](https://github.com/github/spec-kit) | 02-11-2026 |
| 4 | Framework de Evals baseados em modelos de fronteira com rubricas estruturadas | Sim | [OpenAI Evals Framework](https://github.com/openai/evals) | 02-11-2026 |
| 5 | Princípios de IV&V (Independent Verification & Validation) e Red Teaming em IA | Sim | [NIST AI Risk Management Framework (AI RMF 1.0)](https://www.nist.gov/itl/ai-risk-management-framework) | 02-11-2026 |
| 6 | Governança de segurança e guardrails arquiteturais no ciclo de desenvolvimento com IA | Sim | [Google Secure AI Framework (SAIF)](https://safety.google/safety/saif/) | 02-11-2026 |
| 7 | Engenharia de requisitos, atomicidade e verificabilidade conforme padrão ISO 29148 | Sim | [ISO/IEC/IEEE 29148 Systems and Software Engineering](https://standards.ieee.org/ieee/29148/7212/) | 02-11-2026 |

---

## 3. Topologia Operacional do Sub-Agente `sdd-judge`

```mermaid
flowchart TD
    Dev(["Desenvolvedor / IDE"])
    
    subgraph GATES["Pontos de Acionamento SDD"]
        SlashCmd["/vitalia-judge<br/><i>(Invocação Direta)</i>"]
        GateSpecify["Gate specify.md<br/><i>(Pós /vitalia-spec-specify)</i>"]
        GatePlan["Gate plan.md<br/><i>(Pós /vitalia-spec-plan)</i>"]
        GateTasks["Gate tasks.md<br/><i>(Pós /vitalia-spec-tasks)</i>"]
        GateConverge["Gate converge<br/><i>(Pós /vitalia-converge)</i>"]
    end
    
    subgraph GUARDIAN["Contexto Integral & Memória"]
        ConstYAML["constitution.yaml Integral<br/><i>(P00 a P20 sem poda)</i>"]
        Decisions["context_decisions<br/><i>(Memória de ADRs)</i>"]
        Learnings["context_learnings<br/><i>(Erros passados)</i>"]
        Catalog["agents_catalog.yaml"]
    end
    
    subgraph ARTEFATOS["Grafo da Feature 001 (Leitura On-Demand)"]
        CoreDocs["Centrais:<br/>spec.md | plan.md | tasks.md"]
        SupportDocs["Apoio:<br/>requirements.md | research.md<br/>data-model.md | quickstart.md"]
    end
    
    subgraph SUBAGENTE["Sub-Agente sdd-judge (Antigravity Frontier)"]
        Sandwich["Sanduíche Constitucional<br/><i>(Primacy + Recency Guardrails)</i>"]
        InvertedCoT["Inverted Chain-of-Thought<br/><i>(Critique-First ➔ Verdict-Last)</i>"]
        InspectionReport["specs/001-sdd-judge-subagent/Relatório de Inspeção - {fase}.md"]
        HITL["Pausa Mandatória para Decisão Humana<br/><i>(Aprovação HITL Soberana)</i>"]
    end
    
    Dev --> SlashCmd
    GateSpecify --> SlashCmd
    GatePlan --> SlashCmd
    GateTasks --> SlashCmd
    GateConverge --> SlashCmd
    
    SlashCmd --> GUARDIAN
    GUARDIAN --> Sandwich
    ARTEFATOS -.->|"Leitura sob demanda via view_file"| Sandwich
    Sandwich --> InvertedCoT
    
    InvertedCoT --> InspectionReport
    InvertedCoT --> HITL
    HITL -->|"Aprovação explícita"| Dev
```

---

## 4. Requisitos Funcionais Preliminares (Escopo da Feature 001)

- **FR-001 (Numeração Sequencial Padrão Spec-Kit):** Todos os comandos do ciclo SDD operam sob a convenção obrigatória `specs/<NNN>-<slug>/` com 3 dígitos ordenados e registro em `.vitalia/feature.json`.
- **FR-002 (Identidade e Catálogo do Sub-Agente):** Registrar o agente `sdd-judge` em `profiles/agents_catalog.yaml` com status `active`, cargo de Juiz Constitucional Adversarial e model hint `frontier`.
- **FR-003 (Extensão e Skill `/vitalia-judge`):** Criar a extensão e skill do juiz configurando ingestão integral de `constitution` (sem poda de VRAM), `context_decisions`, `context_learnings` e ferramentas nativas de inspeção.
- **FR-004 (Implementação das Técnicas Anti-Diluição):** Injetar no prompt do sub-agente a arquitetura de Sanduíche Constitucional, tags XML estritas com hierarquia de precedência, Inverted Chain-of-Thought e Matriz de Confronto 1-a-1.
- **FR-005 (Módulo de Confronto da Fase 1 - spec.md):** Implementar protocolo de auditoria estrita confrontando a spec contra princípios P00-P20, ADRs prévias, aprendizados de sessões e critérios de aceitação BDD (Given/When/Then).
- **FR-006 (Ingestão Documental Sob Demanda):** O prompt do Sub-Agente deve instruir a IA a identificar e inspecionar sob demanda os arquivos de apoio existentes na pasta da feature (`requirements.md`, `research.md`, `data-model.md`, `quickstart.md`, etc.).
- **FR-007 (Relatório de Inspeção e HITL Soberano):** Toda auditoria deve obrigatoriamente produzir o artefato físico `specs/{feature}/Relatório de Inspeção - {fase}.md` e suspender a execução no chat, aguardando o consentimento humano soberano antes de carimbar o artefato.
- **FR-008 (Reconstrução e Limpeza dos Workflows SDD):** Saneamento de `spec-specify.toml`, `spec-plan.toml`, `spec-tasks.toml` e `converge.toml`, removendo chamadas ao CLI antigo e substituindo-as pela governança do Sub-Agente.

---

## 5. 🚧 Ideias Estacionadas (Out of Scope para esta versão)

- **Inferência Local via Ollama:** Deixada em repouso até o produto transacionar dados reais sob regime LGPD/HIPAA on-premise.
- **Validação Sintática por CLI com Fatiamento de VRAM:** Descontinuada definitivamente em favor do modelo de fronteira na IDE.
