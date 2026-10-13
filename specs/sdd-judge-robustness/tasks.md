<!-- tasks.md | Vitalia SDD v0.6.0 | 12-10-2026 20:54(GMT-04:00) -->
# Tasks: Reforma Estrutural do SDD Judge (Juiz Constitucional Robusto)

**Spec**: [spec.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-robustness/spec.md) | **Plan**: [plan.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-robustness/plan.md)  
**Gerado em**: 12-10-2026 20:54(GMT-04:00)  
**Feature**: `sdd-judge-robustness`  

---

## MVP Scope

> **Implementar Phase 1 + Phase 2 + Phase 3 (US1)** entrega o juiz constitucional funcionando em modo 1-a-1 atômico com varredura completa, eliminando truncamentos arbitrários e a complacência de avaliação.  
> As Phases 4 (US2), 5 (US3) e 6 (Polish/Sync) completam a governança graduada de avisos, a matriz dual para GPU de 6 GB e a sincronização com o kit instalado.

---

## Phase 0: Grounding & Environment

*Verificações de ambiente e validação de pré-requisitos antes de codificar.*

- [X] T000-A Ativar ambiente virtual Python: `source .venv/bin/activate`
- [X] T000-B Verificar versão do interpretador Python: `python3 --version`
- [X] T000-C [P] Validar dependências instaladas no workspace com `pip list`
- [X] T000-D [P] Verificar disponibilidade da API local do Ollama em `http://localhost:11434`
- [X] T000-E [P] Validar alocação de VRAM e presença do modelo `qwen2.5:3b` via `curl -s http://localhost:11434/api/tags` e `nvidia-smi`

---

## Phase 1: Setup & Grounding Contracts

*Estruturação de contratos de dados JSON Schema e tipagens base. Sem label de US.*

- [X] T001 Criar diretório de contratos em `source/src/hooks/sdd_judge/contracts/`
- [X] T002 [P] Copiar e integrar contrato JSON Schema de tarefas para `source/src/hooks/sdd_judge/contracts/task_eval_schema.json`
- [X] T003 [P] Copiar e integrar contrato JSON Schema de seções para `source/src/hooks/sdd_judge/contracts/section_eval_schema.json`
- [X] T004 Implementar dataclass de resposta e telemetria `LLMResponse` em `source/src/hooks/sdd_judge/providers/base.py`

---

## Phase 2: Foundational (Providers Refactor)

*Refatoração da camada de provedores LLM com suporte a Structured Outputs nativo e timeouts. Sem label de US.*

- [X] T005 Refatorar assinatura abstrata `LLMProvider.generate` para aceitar `json_schema` opcional em `source/src/hooks/sdd_judge/providers/base.py`
- [X] T006 Implementar suporte ao parâmetro `format` com JSON Schema e medição de latência em `source/src/hooks/sdd_judge/providers/ollama.py`
- [X] T007 Implementar leitura de `OLLAMA_TIMEOUT` e `OLLAMA_CONNECT_TIMEOUT` do `.env` com tratamento de exceções de conexão em `source/src/hooks/sdd_judge/providers/ollama.py`
- [X] T008 [P] Atualizar provedor Gemini para suportar `responseSchema` no payload REST e medição de latência em `source/src/hooks/sdd_judge/providers/gemini.py`
- [X] T009 Implementar fábrica de provedores `get_provider` com suporte a seleção por tipo de tarefa (reasoning vs coding) em `source/src/hooks/sdd_judge/providers/__init__.py`

---

## Phase 3: User Story 1 — Auditoria Adaptativa & Varredura Completa (US1)

**Story Goal**: Garantir que 100% das tarefas atômicas sejam auditadas individualmente (1-a-1) sem truncamento de arquivos e com relatório consolidado.  
**Independent Test**: Executar `python3 source/src/hooks/sdd_judge/cli.py --mode tasks specs/sdd-judge-robustness/tasks.md` e verificar se todas as tasks aparecem na tabela final sem fatiamento por contagem de caracteres.  
**Referência**: FR-001, FR-002, FR-004, FR-005  

- [X] T010 [US1] Atualizar `source/src/hooks/sdd_judge/evaluators/base.py` para injetar contratos de JSON Schema e decodificar respostas estruturadas de `LLMResponse`
- [X] T011 [P] [US1] Refatorar `source/src/hooks/sdd_judge/evaluators/specify.py` removendo truncamento arbitrário `[:4000]` e avaliando o `spec.md` integralmente
- [X] T012 [P] [US1] Refatorar `source/src/hooks/sdd_judge/evaluators/plan.py` implementando particionamento semântico por seções Markdown (`^##\s+`) sem corte de `[:15000]`
- [X] T013 [US1] Implementar parser de isolamento atômico de tarefas regex `T\d{3}` em `source/src/hooks/sdd_judge/evaluators/tasks.py`
- [X] T014 [US1] Implementar loop de auditoria 1-a-1 com 1 chamada por task e varredura completa sem fail-fast prematuro em `source/src/hooks/sdd_judge/evaluators/tasks.py`
- [X] T015 [US1] Implementar validação determinística de correspondência 1:1 entre tarefas extraídas do arquivo e tarefas auditadas em `source/src/hooks/sdd_judge/evaluators/tasks.py`
- [X] T016 [US1] Renderizar tabela consolidada com todas as tarefas auditadas (T001 a T0N) ao final da execução em `source/src/hooks/sdd_judge/evaluators/tasks.py`

---

## Phase 4: User Story 2 — Governança Graduada de WARN e Suggested Fix (US2)

**Story Goal**: Exibir evidência exata da violação constitucional, nível de severidade do aviso e campo `suggested_fix` pronto para correção.  
**Independent Test**: Submeter uma task inválida e verificar se o parecer exibe `warn_severity`, a regra violada e a sugestão de substituição textual no terminal.  
**Referência**: FR-002, FR-003  

- [X] T017 [US2] Atualizar prompts de sistema em `source/src/hooks/sdd_judge/prompts/tasks.yaml` impondo CoT invertido (`critique` e `evidence` antes de `verdict`)
- [X] T018 [US2] Implementar classificação de severidade (`NONE`, `LOW`, `MEDIUM`, `EXTREME`) e normalização no parser de veredito em `source/src/hooks/sdd_judge/evaluators/base.py`
- [X] T019 [US2] Implementar elevação programática de `WARN` com severidade `EXTREME` para `BLOCK` (`exit code 1`) em `source/src/hooks/sdd_judge/evaluators/tasks.py`
- [X] T020 [US2] Integrar exibição do campo `suggested_fix` nas linhas de inconformidade da tabela consolidada em `source/src/hooks/sdd_judge/evaluators/tasks.py`

---

## Phase 5: User Story 3 — Otimização para Borda (GTX 1060 6GB) & Telemetria Transparente (US3)

**Story Goal**: Permitir que o juiz execute localmente com modelo compacto de raciocínio (`phi4-mini`) sem estourar VRAM e exibindo telemetria honesta.  
**Independent Test**: Executar o juiz localmente e verificar que o banner impresso contém `[Ollama: qwen2.5:3b | X.XXs]` e tempo de inferência por task controlado.  
**Referência**: FR-006, FR-007, NFR-001, NFR-002  

- [X] T021 [US3] Atualizar `source/src/hooks/sdd_judge/providers/ollama.py` para ler `OLLAMA_REASONING_MODEL` (default: `qwen2.5:3b`) e `OLLAMA_CODER_MODEL` (default: `qwen2.5-coder:7b`) de `os.environ`
- [X] T022 [US3] Refatorar `source/src/hooks/sdd_judge/cli.py` para gerar banner dinâmico honesto `--- PARECER DO JUIZ [{provider}: {model} | {latency}s] ---`
- [X] T023 [US3] Implementar padronização de códigos de saída (`0` para PASS/WARN tolerado, `1` para BLOCK/WARN extremo, `2` para falha de infraestrutura) em `source/src/hooks/sdd_judge/cli.py`

---

## Phase 6: Polish, Integration & Synchronization

*Validação end-to-end, conformidade constitucional e sincronização do código mestre com a instalação do kit.*

- [X] T024 [P] Validar cenários do `quickstart.md` executando a suíte de testes em `source/src/hooks/sdd_judge/`
- [X] T025 [P] Verificar integridade dos carimbos `America/Cuiaba (GMT-04:00)` em todos os arquivos Python modificados
- [X] T026 Sincronizar código mestre atualizado para o diretório de instalação do kit: `rsync -av source/ ~/.vitalia/`
- [X] T027 Executar teste de fumaça final do comando do kit: `python3 ~/.vitalia/src/hooks/sdd_judge.py --mode tasks specs/sdd-judge-robustness/tasks.md`

---

## Dependency Graph

```
Phase 0 (Grounding)
       ↓
Phase 1 (Setup & Contracts)
       ↓
Phase 2 (Providers Refactor)
       ↓
Phase 3 (US1: Adaptive & 1-a-1 Audit)
       ↓
Phase 4 (US2: Warning Governance & Suggested Fix)
       ↓
Phase 5 (US3: Edge Hardware & Telemetry)
       ↓
Phase 6 (Polish, Quickstart & Sync)
```

---

## Parallel Execution

As seguintes tarefas podem ser executadas em paralelo por não possuírem dependências cruzadas entre si:
* **Fase 0:** `T000-C`, `T000-D`, `T000-E`
* **Fase 1:** `T002` e `T003`
* **Fase 2:** `T008`
* **Fase 3:** `T011` e `T012`
* **Fase 6:** `T024` e `T025`
