<!-- handoff_transition_topology.md | Vitalia SDD v0.6.0 | 18-10-2026 00:25(GMT-04:00) -->
# Topologia de Handoff, Transição Bidirecional e Nomenclatura de Contexto

**Data:** 18-10-2026 00:25(GMT-04:00)  
**Feature:** `kit-routing-subagents`  
**Status:** ALINHAMENTO ARQUITETURAL  
**Contratos Atendidos:** ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-006

---

## 1. Visão Geral da Topologia Bidirecional

O sistema de handoff do Vitalia Kit opera como uma malha determinística e segura em sistema de arquivos local (`.vitalia/memory/data_storage/handoffs/`), sem dependência de daemons externos (Zero Redis), governado por duas rotas de tráfego complementares:

1. **Fluxo Progressivo (Forward Flow):**  
   `Brainstorming (Supervisor)` ➔ `vitalia-route (Dispatcher)` ➔ `Especialista do Catálogo` ➔ `vitalia-route` ➔ `Pipeline SDD (spec-specify)`.
2. **Fluxo Regressivo / Escalação Invertida (Reverse Flow):**  
   `Agente Executor (spec-implement / pair)` ➔ `vitalia-route` ➔ `Brainstorming (Supervisor)` para repactuação soberana HITL de desvios arquiteturais.
3. **Fallback com Preservação de Contexto (Fallback Flow):**  
   `vitalia-route` ➔ `Brainstorming` quando uma entrada do usuário ou sub-agente for ambígua ou exigir clarificação socrática prévia.

---

## 2. Nomenclatura Semântica dos Arquivos no Filesystem

Para garantir rastreabilidade visual, auditoria e prevenção de colisão em concorrência multi-processo, os arquivos físicos abandonam nomes genéricos e adotam a convenção canônica baseada nos componentes da transição:

```text
.vitalia/memory/data_storage/handoffs/
  ├── handoff_brainstorming_to_vitalia-route_<uuid>.json
  ├── handoff_vitalia-route_to_design-thinking_<uuid>.json
  ├── handoff_design-thinking_to_vitalia-route_<uuid>.json
  ├── handoff_vitalia-route_to_spec-specify_<uuid>.json
  ├── handoff_spec-implement_to_vitalia-route_<uuid>.json
  └── handoff_vitalia-route_to_brainstorming_<uuid>.json
```

### Regra de Formação do Nome:
`handoff_<source_workflow>_to_<target_workflow>_<uuid_8>.json`
- `<source_workflow>`: Basename da extensão emissora (ex: `brainstorming`, `spec-implement`).
- `<target_workflow>`: Basename da extensão receptora (ex: `vitalia-route`, `design-thinking`).
- `<uuid_8>`: Prefixo de 8 caracteres do UUID v4 gerado para a transição.

---

## 3. Direção da Transição e Semântica de `normalized_summary`

No schema `vitalia-handoff-v1.0.0.json`, o campo `envelope.direction` e o campo `intent.normalized_summary` assumem papéis estritos:

| Sentido do Fluxo | `envelope.direction` | `intent.intent_type` | Conteúdo de `intent.normalized_summary` |
|---|---|---|---|
| **Forward: Brainstorming ➔ Route** | `forward` | `brainstorming_to_route` | Caminho do artefato Markdown: `specs/<feat>/research-brainstorming.md` |
| **Forward: Route ➔ Especialista** | `forward` | `route_dispatch` | Instrução de ativação do especialista com referência ao contexto inicial |
| **Reverse: Especialista ➔ Route** | `reverse` | `subagent_response` | Caminho do arquivo JSON com o contexto de transição exportado pelo especialista: `.vitalia/memory/data_storage/handoffs/context_<especialista>_output_<uuid>.json` |
| **Forward: Route ➔ SDD Specify** | `forward` | `sdd_pipeline_advance` | Caminho do artefato consolidado final (PRD ou Síntese) pronto para especificação formal |
| **Reverse: Implement ➔ Route** | `reverse` | `route_to_brainstorming` | Caminho do arquivo JSON com o diagnóstico da divergência: `.vitalia/memory/data_storage/handoffs/divergence_<uuid>.json` |
| **Fallback: Route ➔ Brainstorming**| `fallback`| `route_to_brainstorming` | Resumo textual (até 120 chars) do motivo da necessidade de ideação |

---

## 4. Diagramas Mermaid de Alinhamento

### 4.1. Topologia de Roteamento Completa (Forward & Reverse)

```mermaid
graph TD
    classDef supervisor fill:#2d3748,stroke:#4a5568,stroke-width:2px,color:#fff;
    classDef dispatcher fill:#1a365d,stroke:#2b6cb0,stroke-width:3px,color:#fff;
    classDef specialist fill:#744210,stroke:#d69e2e,stroke-width:2px,color:#fff;
    classDef pipeline fill:#22543d,stroke:#38a169,stroke-width:2px,color:#fff;
    classDef storage fill:#1a202c,stroke:#e2e8f0,stroke-width:1px,stroke-dasharray: 5 5,color:#cbd5e0;

    subgraph MemoryStorage ["Ledger Local de Handoffs (.vitalia/memory/data_storage/handoffs/)"]
        H1["handoff_brainstorming_to_vitalia-route_<uuid>.json<br/>(status: consumed)"]:::storage
        H2["handoff_vitalia-route_to_specialist_<uuid>.json<br/>(status: consumed)"]:::storage
        H3["handoff_specialist_to_vitalia-route_<uuid>.json<br/>(status: consumed)"]:::storage
        H4["handoff_vitalia-route_to_spec-specify_<uuid>.json<br/>(status: pending)"]:::storage
        H5["handoff_spec-implement_to_vitalia-route_<uuid>.json<br/>(Reverse Escalation)"]:::storage
    end

    BS["Nexus Socrático<br/>(/vitalia-brainstorming)"]:::supervisor
    RT["Dispatcher Oficial<br/>(/vitalia-route)"]:::dispatcher
    
    subgraph SpecialistsCatalog ["Especialistas do Catálogo (status: active)"]
        SP_DT["Design Thinking Facilitator<br/>(/vitalia-design-thinking)"]:::specialist
        SP_LC["Literature Curator<br/>(/vitalia-literature-curator)"]:::specialist
        SP_MG["Medical Gate<br/>(/vitalia-medical-gate)"]:::specialist
    end

    subgraph SDDPipeline ["Pipeline SDD Formal"]
        SDD_SPEC["Spec Specify<br/>(/vitalia-spec-specify)"]:::pipeline
        SDD_PLAN["Spec Plan<br/>(/vitalia-spec-plan)"]:::pipeline
        SDD_TASKS["Spec Tasks<br/>(/vitalia-spec-tasks)"]:::pipeline
        SDD_IMP["Spec Implement<br/>(/vitalia-spec-implement)"]:::pipeline
    end

    %% Fluxo Progressivo (Forward)
    BS -->|"1. Síntese + handoff (direction: forward)"| H1
    H1 -->|"2. Consumo e Despacho"| RT
    RT -->|"3. Despacho para Especialista"| H2
    H2 --> SP_DT
    H2 --> SP_LC
    H2 --> SP_MG

    %% Retorno do Especialista (Reverse)
    SP_DT -->|"4. Contexto de Transição JSON (direction: reverse)"| H3
    SP_LC -->|"4. Contexto de Transição JSON (direction: reverse)"| H3
    SP_MG -->|"4. Parecer Clínico JSON (direction: reverse)"| H3
    H3 -->|"5. Avaliação de Maturidade da Concepção"| RT

    %% Avanço para o Pipeline SDD
    RT -->|"6. Concepção Madura ➔ Pipeline SDD"| H4
    H4 --> SDD_SPEC
    SDD_SPEC --> SDD_PLAN --> SDD_TASKS --> SDD_IMP

    %% Escalação Invertida (Reverse Flow)
    SDD_IMP -.->|"7. Desvio Arquitetural! (direction: reverse)"| H5
    H5 -.->|"8. Notificação de Bloqueio"| RT
    RT -.->|"9. Repactuação Soberana HITL"| BS
```

---

### 4.2. Diagrama de Sequência: Ciclo Completo com Especialista e Retorno Inverso

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Desenvolvedor (HITL)
    participant BS as /vitalia-brainstorming (Supervisor)
    participant FS as Local Ledger (data_storage/handoffs/)
    participant RT as /vitalia-route (Dispatcher)
    participant SP as Especialista (ex: /vitalia-design-thinking)
    participant SPEC as /vitalia-spec-specify (SDD Pipeline)

    Note over Dev,BS: Fase 1: Ideação e Concepção Socrática
    Dev->>BS: /vitalia-brainstorming (inicia ideação)
    BS-->>Dev: Turnos Socráticos (STOP -> SCAN -> ASK -> WAIT)
    Dev->>BS: Consenso atingido
    BS->>BS: Grava specs/<feat>/research-brainstorming.md
    BS->>FS: create handoff_brainstorming_to_vitalia-route_<id>.json<br/>[direction: forward | status: pending]
    BS-->>Dev: Exibe síntese e orienta: /vitalia-route --handoff=<id>

    Note over Dev,RT: Fase 2: Despacho do Especialista
    Dev->>RT: /vitalia-route --handoff=<id>
    RT->>FS: validate & consume handoff_brainstorming_to_vitalia-route_<id>.json
    FS-->>RT: status: consumed
    RT->>RT: Avalia guardian_json.sources (Domínio requer PRD/Discovery)
    RT-->>Dev: Propõe Especialista: /vitalia-design-thinking?
    Dev->>RT: "Sim" (Confirmação HITL)
    RT->>FS: create handoff_vitalia-route_to_design-thinking_<id2>.json<br/>[direction: forward | status: pending]
    RT-->>Dev: Execute: /vitalia-design-thinking --handoff=<id2>

    Note over Dev,SP: Fase 3: Atuação do Especialista e Retorno Inverso
    Dev->>SP: /vitalia-design-thinking --handoff=<id2>
    SP->>FS: validate & consume handoff_vitalia-route_to_design-thinking_<id2>.json
    SP->>SP: Conduz Duplo Diamante / Gera PRD
    SP->>FS: Grava context_design-thinking_output_<id3>.json
    SP->>FS: create handoff_design-thinking_to_vitalia-route_<id3>.json<br/>[direction: reverse | summary: path_ao_json | status: pending]
    SP-->>Dev: Concluído! Retorne ao Dispatcher: /vitalia-route --handoff=<id3>

    Note over Dev,SPEC: Fase 4: Despacho para o Pipeline SDD
    Dev->>RT: /vitalia-route --handoff=<id3>
    RT->>FS: validate & consume handoff_design-thinking_to_vitalia-route_<id3>.json
    RT->>RT: Inspeciona context_design-thinking_output_<id3>.json<br/>Identifica que concepção técnica está madura
    RT-->>Dev: Concepção concluída. Avançar para /vitalia-spec-specify?
    Dev->>RT: "Sim" (Confirmação HITL)
    RT->>FS: create handoff_vitalia-route_to_spec-specify_<id4>.json<br/>[direction: forward | status: pending]
    RT-->>Dev: Execute: /vitalia-spec-specify --handoff=<id4>
    Dev->>SPEC: /vitalia-spec-specify --handoff=<id4> (Formalização da Spec)
```

---

### 4.3. Diagrama de Sequência: Escalação Invertida (Reverse Flow por Desvio de Escopo)

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Desenvolvedor (HITL)
    participant IMP as /vitalia-spec-implement (Executor)
    participant FS as Local Ledger (data_storage/handoffs/)
    participant RT as /vitalia-route (Dispatcher)
    participant BS as /vitalia-brainstorming (Supervisor)

    Note over Dev,IMP: Execução Normal do tasks.md
    Dev->>IMP: Executar task T005
    Dev->>IMP: "Altere também a regra de negócio do banco para NoSQL"
    
    Note over IMP: Detecção de Desvio Arquitetural (ADR-004)
    IMP->>IMP: STOP IMEDIATO! Modificação não autorizada no plan.md/ADRs
    IMP->>FS: Grava divergence_<id5>.json (detalhes técnicos da divergência)
    IMP->>FS: create handoff_spec-implement_to_vitalia-route_<id5>.json<br/>[direction: reverse | summary: path_divergence_json | status: pending]
    IMP-->>Dev: 🛑 BLOQUEIO CONSTITUCIONAL: Desvio de escopo detectado.<br/>Execute: /vitalia-route --handoff=<id5>

    Note over Dev,RT: Roteamento da Escalação
    Dev->>RT: /vitalia-route --handoff=<id5>
    RT->>FS: validate & consume handoff_spec-implement_to_vitalia-route_<id5>.json
    RT->>RT: Identifica intent_type: route_to_brainstorming
    RT->>FS: create handoff_vitalia-route_to_brainstorming_<id6>.json<br/>[direction: reverse | status: pending]
    RT-->>Dev: Desvio requer repactuação. Retornar ao Brainstorming?
    Dev->>RT: "Sim"
    RT-->>Dev: Execute: /vitalia-brainstorming --handoff=<id6>

    Note over Dev,BS: Repactuação Soberana de Escopo
    Dev->>BS: /vitalia-brainstorming --handoff=<id6>
    BS->>BS: Lê divergence_<id5>.json referenciado no handoff
    BS-->>Dev: "Identifiquei a proposta de migração NoSQL. Vamos avaliar o trade-off e registrar um novo ADR se aprovado."
```

---

## 5. Matriz de Estados do Arquivo no Filesystem

```mermaid
stateDiagram-v2
    [*] --> Pending: vitalia_handoff.py create<br/>[status: pending, ttl: 3600s]
    
    Pending --> Consumed: vitalia_handoff.py consume<br/>(Mutação Atômica os.replace)
    Pending --> Expired: TTL ultrapassado (> 3600s)
    
    Consumed --> Archival: Limpeza em session-end ou compactação
    Expired --> Purged: TmpCleanup / Purge local
    
    Archival --> [*]
    Purged --> [*]
```

---

## 6. Atualização dos Contratos nos Arquivos TOML

Com este alinhamento formalizado:
1. `source/extensions/brainstorming.toml`:
   - Ao finalizar, gera `specs/<feat>/research-brainstorming.md`;
   - Emite `vitalia_handoff.py create` gerando `handoff_brainstorming_to_vitalia-route_<uuid>.json` com `direction: "forward"`.
2. `source/extensions/vitalia-route.toml`:
   - Inspeciona `direction` e `normalized_summary` (caminho do JSON/Markdown de contexto);
   - Se veio de especialista (`direction: "reverse"` com `intent_type: "subagent_response"`), avalia o JSON emitido pelo especialista. Se a concepção estiver madura, despacha para `/vitalia-spec-specify`;
   - No fallback Nível 3, emite `handoff_vitalia-route_to_brainstorming_<uuid>.json` com `direction: "fallback"`.
3. `source/extensions/spec-implement.toml` e `pair.toml`:
   - Ao identificar desvio, gravam os detalhes da divergência em `divergence_<uuid>.json` e emitem `handoff_spec-implement_to_vitalia-route_<uuid>.json` com `direction: "reverse"` e `intent_type: "route_to_brainstorming"`.
