<!-- architecture-diagrams.md | Vitalia SDD v0.6.0 | 15-10-2026 18:38(GMT-04:00) -->
# Diagramas de Arquitetura: SDD Judge Distribuído & Segregação de Camadas

**Data:** 15-10-2026 18:38(GMT-04:00)  
**Feature:** `sdd-judge-distributed`  
**Documentos Relacionados:**
- [research-brainstorming.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-distributed/research-brainstorming.md)
- [kit_routing_audit.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-distributed/kit_routing_audit.md)

---

## 1. Segregação de Camadas por Cota de Tokens (IDE vs API Externa)

Este diagrama detalha a divisão entre a **cota ampla da IDE Antigravity** (onde o time de engenharia trabalha) e a **cota restrita de API** (reservada exclusivamente para validação constitucional sintética).

```mermaid
flowchart TD
    subgraph CAMADA_IDE ["1. Camada de Criação & Engenharia (Nativa no Antigravity)"]
        direction TB
        DEV["👤 Desenvolvedor"] <--> AGY["⚡ Google Antigravity IDE<br/><b>(Cota Ampla de Tokens / Contexto Denso)</b>"]
        
        subgraph TIME_AGENTES ["Time de Agentes Especializados (Personas / Skills)"]
            MASTER["🏛️ Master AI-Control<br/><i>Tech Lead & Maestro</i>"]
            STARK["🐍 Django-Stark<br/><i>Backend, Models & APIs</i>"]
            VINCI["⚛️ React-Vinci<br/><i>Frontend, UI & Next.js</i>"]
            NOMAD["🐳 Infra-Nomad<br/><i>DevOps, Docker & SRE</i>"]
            CORTEX["🧠 Cortex-Analyst<br/><i>IA, RAG & Prompts</i>"]
            MAESTRO["🎨 Figma-Maestro<br/><i>UX/UI & Design System</i>"]
            
            MASTER --> STARK
            MASTER --> VINCI
            MASTER --> NOMAD
            MASTER --> CORTEX
            MASTER --> MAESTRO
        end

        AGY <--> TIME_AGENTES
    end

    subgraph ARTEFATOS ["Artefatos do Pipeline SDD"]
        SPEC["📋 spec.md"]
        PLAN["🗺️ plan.md"]
        TASKS["✅ tasks.md"]
        CODE["💻 Código / Testes"]
    end

    subgraph CAMADA_JUDGE ["2. Camada de Auditoria Constitucional (API / Local Dedicado)"]
        direction TB
        JUDGE["⚖️ sdd_judge.py<br/><b>(Portão Constitucional Determinístico)</b>"]
        
        subgraph MOTORES_VERIFICACAO ["Motores de Inferência com JSON Schema Estrito"]
            GEMINI_API["☁️ Gemini API (Externa)<br/><i>Reservada apenas para auditorias</i>"]
            OLLAMA_LOCAL["🖥️ Ollama Local (GTX 1060)<br/><i>qwen2.5-coder:3b / phi4-mini</i>"]
        end
        
        JUDGE <--> GEMINI_API
        JUDGE <--> OLLAMA_LOCAL
    end

    TIME_AGENTES -->|"Produz / Edita"| ARTEFATOS
    ARTEFATOS -->|"Enviado para Auditoria"| JUDGE
    JUDGE -->|"Veredito Estruturado:<br/>PASS / WARN / BLOCK"| AGY
```

---

## 2. Orquestração Multi-Agente do SDD Judge via Redis Streams

Este diagrama ilustra a máquina de estados (FSM), a fila assíncrona desacoplada via Redis Streams com Consumer Groups, e a salvaguarda de **5 ciclos com escalada para HITL**.

```mermaid
flowchart TD
    subgraph ETAPA1 ["1. Ingestão & Construção do Envelope"]
        TMD["📄 tasks.md Original"] --> PARSER["Parser Estrutural<br/>(vitalia_hook_runner)"]
        PARSER -->|"Injeta Metadados, US e<br/>Flags de Isenção (ex: P06 UI)"| REDIS_HASH["Redis Hash (Estado)<br/><code>sdd:task:{feature}:{id}</code>"]
        PARSER -->|"Publica Evento Inicial<br/>(Status: INGESTED)"| STREAM["Redis Stream<br/><code>sdd:events:{feature}</code>"]
    end

    subgraph ETAPA2 ["2. Workers Desacoplados (Consumer Groups)"]
        STREAM -->|"Consumer Group: juiz_group"| JUIZ["⚖️ AG. JUIZ<br/>(Distribui Tarefas e Avalia Critérios)"]
        JUIZ -->|"Status: A_ANALISAR"| STREAM

        STREAM -->|"Consumer Group: contesta_group"| CONTESTA["🔍 AG. CONTESTA<br/>(Triagem Rápida via Modelo 3B)"]
        
        CONTESTA -->|"Aprovada"| V_APROV["Marca APROVADA no Hash"]
        V_APROV --> JUIZ

        CONTESTA -->|"Reprovada com Crítica & Fix"| V_REPR["Incrementa cycle_count<br/>Status: REPROVADA"]
        V_REPR --> STREAM

        STREAM -->|"Consumer Group: refatura_group"| REFATURA["🛠️ AG. REFATURA<br/>(Reescreve Definição da Tarefa)"]
        REFATURA -->|"Reapresenta Versão Corrigida"| JUIZ
    end

    subgraph ETAPA3 ["3. Governança, Tolerância a Falhas & HITL"]
        JUIZ -->|"Se cycle_count >= 5<br/>(Sem convergência)"| HITL["🚨 ESCALADA HITL<br/><b>Dossiê Consolidado de Divergências</b><br/>(Comparativo dos 5 debates)"]
        
        HITL -->|"Humano Decide em 1 Comando:<br/>1. Aceita Original<br/>2. Aceita Refaturada<br/>3. Ajusta Manual"| JUIZ

        JUIZ -->|"Quando 100% das Tarefas<br/>estiverem APROVADAS"| FLUSH["💾 Flush Atômico Final<br/>Gravação segura no tasks.md do disco"]
    end
```

---

## 3. Fluxo Ponta a Ponta: Ciclo SDD com o Time de Agentes e os Gates

```mermaid
sequenceDiagram
    autonumber
    actor Dev as 👤 Desenvolvedor
    participant IDE as ⚡ Antigravity (Master + Time)
    participant Redis as 📬 Redis Streams & Hashes
    participant Judge as ⚖️ SDD Judge (API / Ollama)
    participant Disk as 💾 Filesystem (Disco)

    Note over Dev,IDE: FASE 1: Concepção & Planejamento (Dentro da IDE)
    Dev->>IDE: Aciona /vitalia-spec-specify ou /vitalia-spec-plan
    IDE->>IDE: Master AI-Control convoca Stark (Back) e Vinci (Front)
    IDE->>Disk: Grava spec.md e plan.md

    Note over IDE,Judge: FASE 2: Geração & Auditoria de Tarefas (tasks.md)
    Dev->>IDE: Aciona /vitalia-spec-tasks
    IDE->>Disk: Gera rascunho de tasks.md
    IDE->>Redis: Ingestão de tarefas e Envelopes Antialucinação
    
    loop Loop de Contestação e Refatoração (Até 5 ciclos)
        Redis->>Judge: Agente CONTESTA avalia envelope da tarefa
        alt Aprovada de primeira
            Judge->>Redis: Status: APROVADA
        else Divergência / Reprovação
            Judge->>Redis: Status: REPROVADA + Sugestão de Fix
            Redis->>Judge: Agente REFATURA ajusta semântica da tarefa
            Judge->>Redis: Re-avaliação pelo Agente JUIZ
        end
    end

    opt Excesso de Ciclos (cycle_count >= 5)
        Redis->>Dev: Escalada HITL com Dossiê Consolidado
        Dev->>Redis: Decisão humana rápida injetada no Stream
    end

    Redis->>Disk: Flush atômico final no tasks.md aprovado

    Note over Dev,Disk: FASE 3: Implementação (Dentro da IDE)
    Dev->>IDE: Aciona /vitalia-spec-implement
    IDE->>IDE: Stark implementa backend, Vinci implementa frontend
    IDE->>Judge: after_task gate valida conformidade antes de commitar
