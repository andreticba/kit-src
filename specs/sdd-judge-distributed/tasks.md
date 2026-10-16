<!-- tasks.md | Vitalia SDD v0.6.0 | 15-10-2026 21:46(GMT-04:00) -->

# Tasks: Arquitetura Distribuída para Julgamento de Tarefas SDD (sdd-judge-distributed)

**Spec**: [spec.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-distributed/spec.md) | **Plan**: [plan.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-distributed/plan.md) | **Research**: [research.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-distributed/research.md) | **Data Model**: [data-model.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-distributed/data-model.md)  
**Gerado em**: 15-10-2026 21:46(GMT-04:00)

---

## MVP Scope

> Implementar **Phase 0 + Phase 1 + Phase 2 + Phase 3 (US1) + Phase 4 (US2) + Phase 5 (US3)** entrega o motor central funcional de julgamento distribuído em Redis com eliminação de falsos positivos em SLMs locais.  
> As Phases 6 (US4 HITL), 7 (US5 Orquestrador/Flush) e 8 (Polish) completam o ecossistema com interface interativa, barreira atômica e telemetria.

---

## Phase 0: Grounding & Environment

*Verificações de ambiente e integridade operacional antes de qualquer implementação. Sem label de US.*

- [X] T000-A Ativar ambiente virtual Python: `source .venv/bin/activate` em .venv/
- [X] T000-B Verificar versão do interpretador Python no venv: `python --version` garantindo Python 3.10+
- [X] T000-C Validar conectividade e integridade do daemon Redis local na porta 6379 via comando `redis-cli ping`
- [X] T000-D Verificar disponibilidade da API REST do Ollama e dos modelos compactos em `http://localhost:11434/api/tags`
- [X] T000-E Verificar ausência de conflitos de dependências via `pip check` no ambiente Python ativo


---

## Phase 1: Setup & Configurações de Ambiente

*Configuração de pacotes, módulos base e carregamento seguro de variáveis de ambiente. Sem label de US.*

- [X] T001 [P] Criar testes unitários para carregamento de configurações em tests/test_config.py
- [X] T002 Implementar módulo de configuração agnóstica via variáveis de ambiente em source/src/judge/config.py
- [X] T003 [P] Criar inicializador de pacote e exports públicos em source/src/judge/__init__.py
- [X] T004 [P] Criar inicializador do pacote de serviços em source/src/judge/services/__init__.py
- [X] T005 [P] Criar inicializador do pacote de workers em source/src/judge/workers/__init__.py



---

## Phase 2: Foundational & Contratos de Dados

*Validação do esquema JSON do envelope e conexões fundamentais de persistência. Sem label de US.*

- [X] T006 [P] Criar testes unitários para validação de integridade do contrato JSON Schema em tests/test_envelope_schema.py
- [X] T007 Validar o arquivo de contrato JSON Schema Draft 2020-12 em specs/sdd-judge-distributed/contracts/envelope-schema.json
- [X] T008 [P] Criar testes unitários com mocks de conexão Redis em tests/test_redis_client.py
- [X] T009 Implementar wrapper com pool de conexões resiliente em source/src/judge/services/redis_client.py




---

## Phase 3: User Story 1 — Parser Sintético e Envelopamento Anti-Alucinação

**Story Goal**: Transformar linhas isoladas de `tasks.md` em envelopes contextuais ricos com metadados da User Story, tarefa de teste predecessora e flags de escopo negativo (FR-001).  
**Independent Test**: Executar `pytest tests/test_envelope_parser.py` validando extração de envelopes a partir de fixtures markdown com 100% de precisão.  
**Referência**: FR-001, SC-001

- [X] T010 [P] [US1] Criar testes unitários e fixtures markdown para o sintetizador de envelopes em tests/test_envelope_parser.py
- [X] T011 [US1] Implementar parser sintático de tarefas com extração de User Story e teste predecessor em source/src/judge/envelope_parser.py
- [X] T012 [US1] Implementar validação de flags de escopo negativo (contains_secrets=false) e serialização JSON em source/src/judge/envelope_parser.py


---

## Phase 4: User Story 2 — Infraestrutura Concorrente de Mensageria e FSM em Redis

**Story Goal**: Implementar os canais de eventos no Redis Streams com Consumer Groups dedicados e gerenciar estados das tarefas em Redis Hashes com TTL de 24h (FR-002, FR-003).  
**Independent Test**: Executar `pytest tests/test_stream_broker.py` e `pytest tests/test_task_store.py` validando operações de XADD, XREADGROUP, XACK e ciclo de vida do hash.  
**Referência**: FR-002, FR-003, SC-002, SC-003

- [X] T013 [P] [US2] Criar testes unitários de publicação e consumo de Redis Streams em tests/test_stream_broker.py
- [X] T014 [US2] Implementar gerenciador de Redis Streams e criação idempotente de Consumer Groups em source/src/judge/services/stream_broker.py
- [X] T015 [P] [US2] Criar testes unitários para a máquina de estados (FSM) em Redis Hashes em tests/test_task_store.py
- [X] T016 [US2] Implementar repositório TaskStore para persistência de hashes e controle de ciclo de vida em source/src/judge/services/task_store.py




---

## Phase 5: User Story 3 — Loop Adversarial de Juízes, Contestadores e Refaturadores

**Story Goal**: Orquestrar o ciclo multi-agente assíncrono onde o Juiz avalia o envelope, o Contestador analisa falsos positivos e o Refaturador propõe reescrita atômica em até 5 ciclos (FR-004, FR-005).  
**Independent Test**: Executar `pytest tests/test_workers.py` simulando disputa entre Juiz e Contestador até aprovação sem deadlocks.  
**Referência**: FR-004, FR-005, SC-004, SC-005

- [X] T017 [P] [US3] Criar testes unitários para a classe base de workers assíncronos em tests/test_base_worker.py
- [X] T018 [US3] Implementar classe abstrata BaseWorker com loop de consumo XREADGROUP e confirmação XACK em source/src/judge/workers/base_worker.py
- [X] T019 [P] [US3] Criar testes unitários para o trabalhador auditor (Juiz) em tests/test_judge_worker.py
- [X] T020 [US3] Implementar JudgeWorker integrando inferência estruturada de envelopes contextuais em source/src/judge/workers/judge_worker.py
- [X] T021 [P] [US3] Criar testes unitários para o trabalhador de defesa em tests/test_contest_worker.py
- [X] T022 [US3] Implementar ContestWorker para análise de argumentos de defesa e falsos positivos em source/src/judge/workers/contest_worker.py
- [X] T023 [P] [US3] Criar testes unitários para o trabalhador de reescrita em tests/test_refactor_worker.py
- [X] T024 [US3] Implementar RefactorWorker com controle de bounded recursion (limite de 5 ciclos) em source/src/judge/workers/refactor_worker.py




---

## Phase 6: User Story 4 — Resolução Interativa de Escalação Humana (HITL)

**Story Goal**: Apresentar dossiê técnico de impasse no 5º ciclo de divergência e permitir resolução humana acionável via CLI interativa (FR-006).  
**Independent Test**: Executar `pytest tests/test_hitl_resolver.py` com emulação de inputs do terminal para as opções de override e edição.  
**Referência**: FR-006, SC-006

- [X] T025 [P] [US4] Criar testes unitários para o resolvedor interativo de escalação humana em tests/test_hitl_resolver.py
- [X] T026 [US4] Implementar interface CLI HitlResolver com menu de 5 opções e renderização do dossiê em source/src/judge/hitl_resolver.py
- [X] T027 [US4] Integrar transição de status para APROVADA após decisão humana em source/src/judge/hitl_resolver.py



---

## Phase 7: User Story 5 — Orquestrador Central e Barreira de Flush Atômico

**Story Goal**: Coordenar o ciclo de vida completo do pipeline, monitorar a barreira de 100% de aprovação e gravar o arquivo físico atomicamente com backup prévio (FR-007, FR-008).  
**Independent Test**: Executar `pytest tests/test_distributed_orchestrator.py` validando que tasks.md permanece inalterado até aprovação de 100% das tarefas.  
**Referência**: FR-007, FR-008, SC-007, SC-008

- [X] T028 [P] [US5] Criar testes unitários para o orquestrador central e barreira de sincronização em tests/test_distributed_orchestrator.py
- [X] T029 [US5] Implementar DistributedOrchestrator com barreira de sincronização em source/src/judge/distributed_orchestrator.py
- [X] T030 [US5] Implementar persistência atômica via os.replace com criação preventiva de tasks.md.bak em source/src/judge/distributed_orchestrator.py
- [X] T031 [US5] Implementar exportação de histórico arquivado em .vitalia/sessions/shards/ em source/src/judge/distributed_orchestrator.py

---

## Phase 8: Polish, Telemetria & Validação Integrada

*Integração de ponta a ponta, logging estruturado de latência e execução da suíte de validação. Sem label de US.*

- [X] T032 [P] Criar testes de integração end-to-end com a fixture de 3 tarefas em tests/test_integration_quickstart.py
- [X] T033 Implementar telemetria de latência por ciclo e relatório formatado de terminal em source/src/judge/distributed_orchestrator.py
- [X] T034 Executar validação completa do roteiro quickstart contra fixtures em specs/sdd-judge-distributed/quickstart.md
- [X] T035 Sincronizar código-fonte de source/src/judge/ com a distribuição de produção em ~/.vitalia/src/judge/

---

## Dependency Graph

```text
Phase 0 (Grounding)
       ↓
Phase 1 (Setup)
       ↓
Phase 2 (Foundational & Contratos)
       ↓
Phase 3 (US1: Parser & Envelopes)
       ↓
Phase 4 (US2: Redis Streams & FSM)
       ↓
Phase 5 (US3: Loop Adversarial Multi-Agente)
       ↓
Phase 6 (US4: Resolução HITL CLI)
       ↓
Phase 7 (US5: Orquestrador Central & Flush Atômico)
       ↓
Phase 8 (Polish, Telemetria & Validação Integrada)
```

---

## Parallel Execution

As tarefas marcadas com o identificador `[P]` operam sobre arquivos independentes e sem dependências mútuas bloqueantes, podendo ser executadas em paralelo dentro da mesma fase:
- **Phase 1**: `T001`, `T003`, `T004`, `T005`
- **Phase 2**: `T006`, `T008`
- **Phase 3**: `T010`
- **Phase 4**: `T013`, `T015`
- **Phase 5**: `T017`, `T019`, `T021`, `T023`
- **Phase 6**: `T025`
- **Phase 7**: `T028`
- **Phase 8**: `T032`
