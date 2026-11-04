# Diagrama de Interação de Ponta a Ponta — Vitalia SPEC Kit (v0.0.1)

> **Data/Hora de Geração:** `03-11-2026 19:30:00(GMT-04:00)` | **Fuso Horário:** America/Cuiaba `(GMT-04:00)`

---

## 1. Diagrama Geral de Interação (Mermaid Puro — Tema Nativo)

```mermaid
flowchart TD
    subgraph FASE_1 ["FASE 1: IDEACAO E EXPLORACAO SOCRATICA"]
        U["Usuario (Ideia / Necessidade)"] --> B["/vitalia-brainstorming<br/>(Nexus Socratico)"]
        B --> B_TEST{"Restam duvidas?<br/>(Maximo 3 perguntas/turno)"}
        B_TEST -- "Sim" --> B
        B_TEST -- "Nao: Aprovado pelo Usuario" --> B_OUT["research-brainstorming.md<br/>+ Registro de Handoff"]
    end

    subgraph FASE_2 ["FASE 2: DESPACHO DETERMINISTICO"]
        B_OUT --> R["/vitalia-route<br/>(Despachante Oficial)"]
        R --> R_CAT["Consulta Catalogo:<br/>brainstorming_intents.yaml<br/>agents_catalog.yaml<br/>routing_table.yaml"]
        R_CAT --> R_DEC{"Qual o Dominio da Demanda?"}
    end

    subgraph FASE_3 ["FASE 3: ESPECIALISTAS OU REGENCIA"]
        R_DEC -- "Dominio Clinico" --> E_MED["/vitalia-medical-gate<br/>(Risco Clinico e HITL)"]
        R_DEC -- "Revisao Literatura" --> E_LIT["/vitalia-literature-curator<br/>(PRISMA e Fichamento)"]
        R_DEC -- "Design Thinking" --> E_DT["/vitalia-design-thinking<br/>(PRD e Descoberta)"]
        R_DEC -- "Desenvolvimento de Software" --> ARC["/vitalia-architect<br/>(Vitalia Architect: Maestro SDD)"]

        E_MED -. "Parecer Clinico" .-> ARC
        E_LIT -. "Evidencias Cientificas" .-> ARC
        E_DT -. "PRD e Personas" .-> ARC
    end

    subgraph FASE_4 ["FASE 4: CICLO SDD FORMAL & AUDITORIA JUDGE"]
        ARC --> S_SPEC["1. /vitalia-spec-specify<br/>(Le research-brainstorming.md)"]
        S_SPEC --> J_SPEC["Judge: Auditoria Specify<br/>(Inverted CoT)"]
        J_SPEC -- "PASS / WARN (Aprovado HITL)" --> S_PLAN["2. /vitalia-spec-plan<br/>(Arquitetura e OpenAPI 3.0)"]
        
        S_PLAN --> J_PLAN["Judge: Auditoria Plan<br/>(Inverted CoT)"]
        J_PLAN -- "PASS / WARN (Aprovado HITL)" --> S_TASKS["3. /vitalia-spec-tasks<br/>(TDD Red ou Bug Repro)"]
        
        S_TASKS --> J_TASKS["Judge: Auditoria Tasks<br/>(Inverted CoT)"]
        J_TASKS -- "PASS / WARN (Aprovado HITL)" --> S_IMPL["4. /vitalia-spec-implement<br/>(Execucao de Codigo)"]
        
        S_IMPL --> S_CONV["5. /vitalia-converge<br/>(Reconciliacao de Codigo)"]
        S_CONV --> J_CONV["Judge: Auditoria Converge<br/>(Inverted CoT)"]
    end

    subgraph MEMORIA ["INFRAESTRUTURA DE MEMORIA 3-TIER (PARTICAO POR MACHINE_ID)"]
        M_SESSION[".vitalia/memory/session/<br/>Repo Git Compartilhado:<br/>Shards e Contexto da Equipe"]
        M_STORAGE[".vitalia/memory/data_storage/<br/>Repo Git Transitorio:<br/>Handoffs e Context Lifting"]
    end

    B -. "Le/Grava Memoria" .-> M_SESSION
    B_OUT -. "Handoff Forward" .-> M_STORAGE
    S_IMPL -. "Context Lifting" .-> M_STORAGE
    J_CONV -. "Learnings e Decisions" .-> M_SESSION
```

---

## 2. Diagrama de Regência da Engenharia (Architect e Especialistas)

```mermaid
flowchart TD
    ARC_NODE["/vitalia-architect<br/>(Vitalia Architect: Tech Lead e Maestro)"] --> SPEC_IN["Entrada da Spec Aprovada<br/>(Requisitos Funcionais e Criterios de Aceite)"]

    SPEC_IN --> ROUTE_DOMAIN{"Decomposicao por Dominio da Tarefa"}

    ROUTE_DOMAIN -- "Backend / APIs / DB" --> STARK["Django-Stark<br/>(Backend Python, DRF, Celery, Postgres, TDD)"]
    ROUTE_DOMAIN -- "Frontend / Telas" --> VINCI["React-Vinci<br/>(Next.js, TypeScript, Tailwind, A11y, UI)"]
    ROUTE_DOMAIN -- "DevOps / Containers" --> NOMAD["Infra-Nomad<br/>(Docker Compose, CI/CD, IaC, Local-First)"]
    ROUTE_DOMAIN -- "RAG / Embeddings" --> CORTEX["Cortex-Analyst<br/>(NLP, pgvector, Chunking, Triage)"]
    ROUTE_DOMAIN -- "Design System / UX" --> MAESTRO["Figma-Maestro<br/>(Design Tokens, WCAG, Mockups)"]

    STARK --> REVIEW["Revisao do Maestro (vitalia-architect)<br/>+ Auditoria /vitalia-judge"]
    VINCI --> REVIEW
    NOMAD --> REVIEW
    CORTEX --> REVIEW
    MAESTRO --> REVIEW

    REVIEW -- "Aprovado" --> COMMIT["Integracao e Conclusao da Task"]
```

---

## 3. Tabela Sequencial do Fluxo de Trabalho

| Passo | Agente Executor | Missão Principal | Artefato Gerado / Consumido |
|---|---|---|---|
| **1. Concepção** | `/vitalia-brainstorming` | Ideação aberta e questionamento socrático em turnos de até 3 perguntas. | Gera `specs/<feature>/research-brainstorming.md`. |
| **2. Despacho** | `/vitalia-route` | Classifica a intenção e propõe ao usuário o próximo especialista. | Consome o handoff e os catálogos YAML. |
| **3. Domínio Clínico / Pesquisa** | `medical-gate` ou `literature-curator` | Valida risco de saúde ou reúne literatura científica indexada (se aplicável). | Parecer de risco (`DRAFT`) ou fichamento PRISMA. |
| **4. Maestro SDD** | `/vitalia-architect` (Vitalia Architect) | Recebe os consensos, avalia viabilidade técnica e inicia o ciclo SDD. | Abre o diretório da feature e chama `/vitalia-spec-specify`. |
| **5. Especificação** | `/vitalia-spec-specify` | Modela a spec formal com User Stories e cenários Given-When-Then. | Gera `spec.md` e checklist ISO 29148. |
| **6. Auditoria Spec** | `/vitalia-judge --mode=specify` | Avalia conformidade constitucional e ISO 29148 com Inverted CoT. | `Relatório de Inspeção - specify.md` (Pausa HITL). |
| **7. Planejamento** | `/vitalia-spec-plan` | Define arquitetura técnica e contratos de interface em OpenAPI 3.0 puro. | Gera `plan.md` e esquemas em `contracts/`. |
| **8. Auditoria Plan** | `/vitalia-judge --mode=plan` | Valida decisões técnicas e ausência de esquemas poluídos com `$schema`. | `Relatório de Inspeção - plan.md` (Pausa HITL). |
| **9. Decomposição** | `/vitalia-spec-tasks` | Decompõe o plano em tarefas atômicas (T001, T002) com Red Phase ou Bug Repro. | Gera `tasks.md`. |
| **10. Auditoria Tasks** | `/vitalia-judge --mode=tasks` | Valida atomicidade, ordem de dependência e cobertura de User Stories. | `Relatório de Inspeção - tasks.md` (Pausa HITL). |
| **11. Implementação** | `/vitalia-spec-implement` | Executa o código e valida testes verdes antes de marcar `[X]`. | Código em produção e testes unitários. |
| **12. Reconciliação** | `/vitalia-converge` | Auditoria quadridimensional entre código real, spec, plan e tasks. | Reconciliação de `tasks.md` via Sub-Agente Judge. |
