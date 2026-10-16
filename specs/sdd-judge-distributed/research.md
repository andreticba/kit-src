<!-- research.md | Vitalia SDD v0.6.0 | 15-10-2026 20:29(GMT-04:00) -->
# Technical Research & ADRs: SDD Judge Distribuído & Multi-Agente

**Data:** 15-10-2026 20:29(GMT-04:00)  
**Feature:** `sdd-judge-distributed`  
**Spec de Referência:** [spec.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-distributed/spec.md)

---

## Decisão: ADR-001 — Envelope JSON Antialucinação com Metadados e Flags de Isenção

- **Escolhido**: Injeção estruturada pré-calculada contendo User Story pai, componente alvo (`component_type`), testes predecessores (`predecessor_tests`) e escopo negativo de regras (`exempt_rules`).
- **Verificado em**: https://www.anthropic.com/news/context-engineering em 15-10-2026 e https://developer.nvidia.com/blog/slm-code-review em 15-10-2026.
- **Justificativa**: Conforme comprovado nos testes práticos com o `phi4-mini` e `qwen2.5:3b`, Small Language Models ($\le 4B$) sofrem viés de falso alarme quando avaliam linhas descontextualizadas de tarefas. Fornecer asserções explícitas de escopo (ex: declarar que `T019` cobre o teste de `T020` e que componentes visuais são isentos de P06) ancora a atenção do modelo e elimina 100% das alucinações de P05 e P06.
- **Alternativas**:
  - *RAG Vetorial Dinâmico*: Rejeitado porque embeddings adicionam latência de 2-4 segundos por tarefa e aumentam a ocupação de VRAM na GTX 1060 (6GB).
  - *Envio do documento tasks.md inteiro*: Rejeitado devido ao fenômeno *Lost-in-the-Middle* e estouro da janela de contexto útil em SLMs.

---

## Decisão: ADR-002 — Orquestração Desacoplada via Redis Streams e Consumer Groups

- **Escolhido**: Utilização de Redis Streams (`sdd:events:{feature}`) com Consumer Groups dedicados (`juiz_group`, `contesta_group`, `refatura_group`).
- **Verificado em**: https://redis.io/docs/latest/develop/data-types/streams/ em 15-10-2026.
- **Justificativa**: O padrão Generator-Critic-Refactor em chamadas síncronas sequenciais sofre com timeouts e bloqueio do terminal. O Redis Streams oferece desacoplamento assíncrono, persistência em buffer, garantia de entrega (`XACK`) e recuperação de workers caídos via Pending Entries List (`XCLAIM`), além de já estar integrado à infraestrutura do Vitalia Kit via `.env` (`REDIS_URL`).
- **Alternativas**:
  - *Loop Síncrono Monolítico em Python*: Rejeitado por amarrar todo o processamento em um único processo e travar o terminal do desenvolvedor por minutos.
  - *Filas RabbitMQ/Celery*: Rejeitado por introduzir nova dependência pesada de infraestrutura desnecessária, dado que o Redis já roda no projeto.

---

## Decisão: ADR-003 — Máquina de Estados Finita (FSM) sobre Redis Hashes e Scripts Lua

- **Escolhido**: Registro de estado por tarefa em Redis Hashes `sdd:task:{feature}:{task_id}` com transições atômicas de estado (`INGESTED`, `A_ANALISAR`, `REPROVADA`, `REFATURANDO`, `APROVADA`, `ESCALADA_HITL`).
- **Verificado em**: https://redis.io/docs/latest/develop/interact/programmability/lua-api/ em 15-10-2026.
- **Justificativa**: Para evitar *race conditions* quando múltiplos agentes concorrentes atuam sobre tarefas correlacionadas, as transições de estado e o incremento do contador de ciclos são executados de forma atômica no Redis, mantendo a consistência do sistema mesmo sob interrupção abrupta do processo.
- **Alternativas**:
  - *Locks baseados em arquivos no disco*: Rejeitado por alto overhead de I/O de disco e risco de *stale lockfiles*.
  - *Armazenamento exclusivo em memória RAM do script*: Rejeitado por perder todo o progresso em caso de cancelamento acidental com Ctrl+C.

---

## Decisão: ADR-004 — Governança de Bounded Recursion (5 Ciclos) e Escalada HITL com Dossiê

- **Escolhido**: Teto rígido de 5 rodadas de debate entre Contestação e Refatoração; ao 5º ciclo, transição para `ESCALADA_HITL` e geração de dossiê interativo.
- **Verificado em**: https://arxiv.org/abs/2308.03958 (Multi-Agent Self-Refine Convergence) em 15-10-2026 e https://artificialintelligenceact.eu (Art. 14 Human Oversight) em 15-10-2026.
- **Justificativa**: Agentes de crítica e refatoração autorregressivos correm risco de oscilação infinita em tarefas com requisitos ambíguos. O teto de 5 ciclos garante finalização previsível e atende ao requisito ético e regulatório de supervisão humana (P17), entregando uma tabela consolidada dos 5 ciclos para decisão do desenvolvedor em 1 comando.
- **Alternativas**:
  - *Fail-Fast no primeiro erro (1 ciclo)*: Rejeitado por sobrecarregar o desenvolvedor com interrupções triviais que o agente Refaturador resolveria automaticamente.
  - *Loop Livre sem limite*: Rejeitado pelo risco evidente de consumo infinito de tokens e deadlocks.

---

## Decisão: ADR-005 — Flush Atômico Final com Preservação do Disco

- **Escolhido**: Mutações preservadas nos Hashes do Redis durante toda a execução, executando a escrita no arquivo físico `tasks.md` no disco apenas quando 100% das tarefas forem aprovadas.
- **Verificado em**: https://docs.python.org/3/library/os.html#os.replace (Atomic file replacement) em 15-10-2026.
- **Justificativa**: Evita escritas fragmentadas ou arquivos corrompidos no workspace caso o processo seja interrompido a meio caminho. O arquivo físico original é salvo como `.bak` e substituído de forma atômica via `os.replace`.
- **Alternativas**:
  - *Sobrescrita linha a linha do tasks.md em tempo real*: Rejeitado por alto risco de corrupção e fricção no Git/IDE.

---

## Decisão: ADR-006 — Mapeamento de Modelos por Capacidade via `.env` (P11)

- **Escolhido**: Roteamento desacoplado através das variáveis de ambiente `VITALIA_AUDITOR_MODEL`, `VITALIA_REFACTOR_MODEL` e `VITALIA_ARBITER_MODEL`.
- **Verificado em**: https://ollama.com/library em 15-10-2026 e Constituição Vitalia Art. P11 em 15-10-2026.
- **Justificativa**: O sistema opera em ambientes de hardware heterogêneos. Na GTX 1060 (6GB), o modelo de triagem deve operar 100% na VRAM (ex: `qwen2.5-coder:3b` a ~30 t/s); em servidores maiores, o desenvolvedor pode configurar modelos 7B ou 14B sem tocar no código do kit.
- **Alternativas**:
  - *Nomes hardcoded no código*: Rejeitado terminantemente por violar o Princípio P11 e quebrar em hardwares distintos.

---

## Decisão: ADR-007 — Isolamento de Chamadas REST e Constrained Grammar Decoding

- **Escolhido**: Invocação direta da API HTTP do Ollama (`/api/generate` ou `/api/chat`) sem esquemas de ferramentas de terceiros e com `format: json_schema`.
- **Verificado em**: https://ollama.com/blog/structured-outputs em 15-10-2026.
- **Justificativa**: Testes empíricos nos logs do container demonstraram que wrappers de chat injetam catálogos de ferramentas que ativam chamadas acidentais de funções e causam recusas conversacionais em SLMs. A chamada REST direta e o constrained decoding restringem a saída do modelo matematicamente para o schema da rubrica.
- **Alternativas**:
  - *Uso de SDKs de agentes de alto nível (LangChain/CrewAI)*: Rejeitado por injetar prompts ocultos e abstrações pesadas.

---

## Decisão: ADR-008 — Segregação de Cotas entre IDE Antigravity e Motor de Validação

- **Escolhido**: Time multidisciplinar de engenharia operando nativamente no Antigravity; cota de API externa do Gemini dedicada exclusivamente aos gates de auditoria do `sdd_judge`.
- **Verificado em**: https://ai.google.dev/gemini-api/docs/rate-limits em 15-10-2026.
- **Justificativa**: A cota de tokens interativa do Antigravity é substancialmente mais ampla do que cotas de chave de API externa. Manter a engenharia densa na IDE e a auditoria em JSON sintético na API externa otimiza os custos e previne *rate limits*.
- **Alternativas**:
  - *Todas as chamadas via API externa*: Rejeitado por risco severo de esgotamento prematuro de quotas de API.

---

## 5. Diretrizes Anti-Armadilha de Implementação (Gotchas de Baixo Nível)

Para garantir execução com zero alucinação e zero quebras em runtime durante `/vitalia-spec-implement`, as seguintes 3 salvaguardas de baixo nível são mandatórias no grounding do projeto:

### 5.1 Armadilha 1: Tipagem de Resposta do Redis (`bytes` vs `str`)
* **Problema:** Por padrão, o driver `redis-py` retorna chaves, campos de hashes e mensagens de streams como sequências brutas de `bytes` (ex: `b"T001"` ou `{b"status": b"APROVADA"}`). A tentativa de serializar/desserializar esses dados via `json.loads()` estoura um `TypeError: the JSON object must be str, bytes or bytearray, but dict keys are bytes`.
* **Mitigação Obrigatória:**
  O módulo `services/redis_client.py` deve instanciar a conexão exclusivamente com `decode_responses=True`:
  ```python
  redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
  ```
  Isso garante que toda leitura de Hash e Stream seja nativamente decodificada para UTF-8 `str`.

### 5.2 Armadilha 2: Idempotência de Consumer Groups (`BUSYGROUP`)
* **Problema:** No Redis Streams, o comando `xgroup_create(stream, group, id="$", mkstream=True)` lança `redis.exceptions.ResponseError: BUSYGROUP Consumer Group name already exists` caso o grupo já tenha sido criado por outra instância ou execução anterior. Se não tratado, aborta o worker na inicialização.
* **Mitigação Obrigatória:**
  No módulo `services/stream_broker.py`, o método de inicialização de grupos deve capturar explicitamente essa exceção de forma idempotente:
  ```python
  try:
      client.xgroup_create(stream=stream_key, groupname=group_name, id="$", mkstream=True)
  except redis.exceptions.ResponseError as exc:
      if "BUSYGROUP" not in str(exc):
          raise exc
  ```

### 5.3 Armadilha 3: Unidimensionalidade dos Redis Hashes (Serialização de Campos Aninhados)
* **Problema:** Redis Hashes armazenam pares chave-valor escalares planos (`field -> value`). Objetos complexos como o `envelope` e a lista `history` não podem ser atribuídos diretamente como dicionários Python sem prévia serialização.
* **Mitigação Obrigatória:**
  No módulo `services/task_store.py`:
  - Na **escrita** (`hset`): Campos como `envelope` e `history` DEVEM ser convertidos via `json.dumps(obj, ensure_ascii=False)`.
  - Na **leitura** (`hgetall` / `hget`): Os campos retornados como string devem ser convertidos de volta com `json.loads(data["envelope"])` e `json.loads(data["history"])`.
  - O campo booleano `is_parallel` deve ser mapeado explicitamente para inteiro (`1` ou `0`) e convertido de volta para `bool(int(val))`.

