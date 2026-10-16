<!-- plan.md | Vitalia SDD v0.6.0 | 15-10-2026 20:35(GMT-04:00) -->

# Implementation Plan: Arquitetura Distribuída para Julgamento de Tarefas SDD (sdd-judge-distributed)

**Branch**: `sdd-judge-distributed` | **Data**: 15-10-2026 20:35(GMT-04:00) | **Spec**: [spec.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-distributed/spec.md) | **Research**: [research.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-distributed/research.md)

---

## 1. Summary

Implementação da arquitetura distribuída e assíncrona de julgamento de tarefas do Vitalia SDD Kit (`sdd-judge-distributed`), eliminando falsos positivos sistêmicos em SLMs locais (P05 Test-First e P06 Secrets) e latências excessivas na GPU NVIDIA GTX 1060 (6GB VRAM):
1. **Parser com Envelopes Anti-Alucinação:** Injeção contextual estruturada (User Story pai, predecessora de teste, flags de escopo negativo) via JSON Schema.
2. **Ciclo Multi-Agente em Redis Streams:** Processamento assíncrono via Consumer Groups (`juiz_group`, `contesta_group`, `refatura_group`).
3. **FSM em Memória (Redis Hashes):** Transições de estado com isolamento absoluto do disco físico (`tasks.md`) até aprovação de 100% das tarefas.
4. **Resolução Humana Deliberada (HITL):** Escalação no 5º ciclo de impasse com dossiê interativo (P17).
5. **Roteamento Agnóstico via .env:** Modelos desacoplados (`VITALIA_AUDITOR_MODEL`, `VITALIA_REFACTOR_MODEL`, `VITALIA_ARBITER_MODEL`) (P11).
6. **Segregação de Quotas:** Agentes de engenharia nativos no Antigravity; API externa restrita aos gates de validação.

---

## 2. Technical Context & Verificação Externa (P03)

* **Linguagem & Runtime:** Python 3.10+ (compatível com 3.10 a 3.14).
* **Dependências & Protocolo de Verificação Externa (P03):**
  * `redis` (v5.0.1+): Verificado em [redis.io/docs](https://redis.io/docs/latest/develop/data-types/streams/) para Consumer Groups assíncronos.
  * `requests` (v2.31.0+): Verificado para chamadas REST ao Ollama e Gemini API.
  * `json-schema` (Draft 2020-12): Verificado em [json-schema.org](https://json-schema.org/draft/2020-12/release-notes).
* **Infraestrutura & Hardware (P11):** Redis local via `REDIS_URL` e SLMs locais via `OLLAMA_HOST` (`OLLAMA_NUM_PARALLEL=1`).
* **Segurança & Segredos (P06):** Zero credenciais em código; carregamento 100% via `os.environ`.
* **Metas de Desempenho:** Inferência $\le 2.0\text{s}$ na GTX 1060, VRAM $\le 3.0\text{ GB}$, 0% de falso positivo em P05.

---

## 3. Constitution Check (Auditoria Pré-Implementação)

| Princípio | Status | Evidência / Salvaguarda no Plano |
| :--- | :---: | :--- |
| **P01 (SDD Inviolability)** | **PASS** | Rastreabilidade total derivando de `spec.md` (FR-001 a FR-008) e `research.md`. |
| **P02 (User Value)** | **PASS** | `tasks.md` em disco intacto até 100% de aprovação; zero corrupção de arquivos. |
| **P03 (External Grounding)** | **PASS** | Bibliotecas, schemas e endpoints verificados com links oficiais ativos. |
| **P04 (Timestamp GMT-04:00)** | **PASS** | Cabeçalho canônico `15-10-2026 20:35(GMT-04:00)` presente nos artefatos. |
| **P06 (Secrets Protection)** | **PASS** | Parser valida `contains_secrets=false`; credenciais via `os.environ`. |
| **P11 (Hardware Agnosticism)** | **PASS** | Sem modelo ou caminho hardcoded; configurável via `.env` (`VITALIA_AUDITOR_MODEL`). |
| **P15 (Observability)** | **PASS** | Telemetria de latência por ciclo e persistência de shards em disco. |
| **P16 (Mermaid Rigor)** | **PASS** | Sintaxe estrita com rótulos entre aspas duplas `""`. |
| **P17 (HITL Escalation)** | **PASS** | Escalação com dossiê e parada controlada no 5º ciclo de divergência. |


---

## 4. Technical Decisions (ADRs Fundamentadas em research.md)

* **ADR-001: Envelopamento Estruturado Anti-Alucinação** — Parser sintetiza metadados e valida que não há segredos nem dados pessoais sensíveis (`negative_scope_flags`), eliminando falsos positivos de P05 e P06. Grounding: [Ollama Structured Outputs](https://ollama.com/blog/structured-outputs).
* **ADR-002: Orquestração Distribuída via Redis Streams** — Uso de Consumer Groups (`juiz_group`, `contesta_group`, `refatura_group`) sobre `sdd:events:{feature}` com URL configurável via `REDIS_URL` (P11). Grounding: [Redis Streams Specification](https://redis.io/docs/latest/develop/data-types/streams/).
* **ADR-003: FSM em Redis Hashes e Flush Atômico em Disco** — Estados em memória (`sdd:task:{feature}:{task_id}`). Flush para `tasks.md` apenas com barreira de 100% APROVADAS e backup prévio `.bak`. Grounding: [Python os.replace](https://docs.python.org/3/library/os.html#os.replace).
* **ADR-004: Bounded Recursion no Loop Adversarial (5 ciclos)** — Limite estrito de 5 tentativas antes de transitar para `ESCALADA_HITL`, evitando deadlocks de IA. Grounding: [Martin Fowler Circuit Breaker](https://martinfowler.com/bliki/CircuitBreaker.html).
* **ADR-005: Resolutor Interativo de Escalação Humana (HITL CLI)** — Módulo `hitl_resolver` com menu de desempate e override constitucional (P17). Grounding: [Python Argparse](https://docs.python.org/3/library/argparse.html).
* **ADR-006: Roteamento Agnóstico por Variáveis de Ambiente** — Variáveis canônicas `VITALIA_AUDITOR_MODEL`, `VITALIA_REFACTOR_MODEL` e `VITALIA_ARBITER_MODEL` em `.env`. Grounding: [Twelve-Factor App Config](https://12factor.net/config).
* **ADR-007: Segregação de Quotas de Contexto e Inferência** — Agentes de engenharia executam no Antigravity (alta quota); API externa e Ollama exclusivos para gates do SDDJudge. Grounding: [Gemini API Quotas](https://ai.google.dev/pricing).
* **ADR-008: Configuração Otimizada do Ollama para Borda (GTX 1060)** — `OLLAMA_NUM_PARALLEL=1` para garantir contexto de 4096 tokens sem truncamento em SLMs de 3B. Grounding: [Ollama FAQ](https://github.com/ollama/ollama/blob/main/docs/faq.md).

---

## 5. Project Structure & Phases

### Módulos Principais (`source/src/judge/`)
* `config.py`: Configurações e variáveis de ambiente (P06/P11).
* `envelope_parser.py`: Parser contextual de TaskEnvelope e filtro de segredos.
* `distributed_orchestrator.py`: Orquestrador central, FSM e barreira atômica.
* `hitl_resolver.py`: CLI interativa para resolução HITL (P17).
* `services/`: `redis_client.py` (conexão resiliente), `stream_broker.py` (consumer groups), `task_store.py` (hashes e barreira).
* `workers/`: `judge_worker.py`, `contest_worker.py`, `refactor_worker.py`.

### Fases de Implementação
1. **Fase 1 (Setup & Contratos):** `config.py`, validação de `envelope-schema.json`, testes do parser.
2. **Fase 2 (Redis Engine & FSM):** `redis_client.py`, `task_store.py`, `stream_broker.py`, concorrência.
3. **Fase 3 (Workers & Loop Adversarial):** `judge_worker.py`, `contest_worker.py`, `refactor_worker.py`.
4. **Fase 4 (Orquestrador & HITL CLI):** `distributed_orchestrator.py`, `hitl_resolver.py`, flush atômico e backup.
5. **Fase 5 (Integração & Quickstart):** Validação ponta a ponta com fixture `tests/fixtures/sample_tasks.md`.


---

## 6. Architecture & Event Flow

O fluxo de eventos entre os componentes obedece à especificação formal detalhada com diagramas Mermaid em [architecture-diagrams.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-distributed/architecture-diagrams.md):
1. **Ingestão:** Orquestrador cria hashes `sdd:task:{feature}:{id}` e publica `TASK_INGESTED`.
2. **Juiz:** Avalia envelope contextual; se conforme $\to$ `APROVADA`; se não $\to$ `REPROVADA` (P15).
3. **Contestador & Refaturador:** Analisam tese de defesa e geram reescrita atômica da tarefa.
4. **Circuito Bounded (5 ciclos):** Se impasse persistir $\to$ `ESCALADA_HITL` para desempate do usuário (P17).
5. **Flush Atômico:** Barreira de 100% `APROVADA` dispara backup e sobrescrita atômica de `tasks.md` (P02).

