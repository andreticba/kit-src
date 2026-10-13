<!-- spec.md | Vitalia SDD v0.6.0 | 12-10-2026 20:26(GMT-04:00) -->
# Especificação Funcional: Reforma Estrutural do SDD Judge (Juiz Constitucional Robusto)

**Data:** 12-10-2026 20:26(GMT-04:00)  
**Feature:** `sdd-judge-robustness`  
**Status:** DRAFT (Aguardando Aprovação)  
**Preset:** `software`  
**Documentos Relacionados:**
- [research-brainstorming.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-robustness/research-brainstorming.md)
- [grounding-dossier.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-robustness/grounding-dossier.md)

---

## 1. Contexto e Objetivo (O Quê e Por Quê)

### 1.1 Contexto
O Vitalia SDD Kit utiliza o componente `sdd_judge` como o gatekeeper constitucional responsável por auditar artefatos de especificação (`spec.md`), planejamento (`plan.md`), tarefas atômicas (`tasks.md`) e código implementado (`converge`, `after_task`). No estado atual, o avaliador sofre de vulnerabilidades críticas que descaracterizam sua função de guardião:
1. **Complacência e Sycophancy:** Uso indiscriminado do modelo coder (`qwen2.5-coder:7b`) para auditorias dedutivas, favorecendo respostas superficiais (`VEREDICTO_FINAL: PASS`).
2. **Gargalo de Hardware (GTX 1060 6GB):** Contextos longos extrapolam a VRAM disponível, provocando *CPU offloading* ou truncamento silencioso.
3. **Ausência de Enforcement de Raciocínio (Zero CoT):** Validação por regex frouxo que ignora se os itens foram auditados.
4. **Ilusão de Observabilidade:** Banner fixo alegando uso da Google Gemini API mesmo durante execução local via Ollama.
5. **Truncamento Cego:** Fatiamento arbitrário de strings (`[:15000]`), descartando tarefas e decisões do final do documento.

### 1.2 Objetivo
Transformar o `sdd_judge` em um juiz constitucional determinístico e rigoroso, adaptando a estratégia de avaliação à semântica real de cada artefato (spec holística, plan por seções, tasks atômica 1-a-1), implementando *Structured Outputs* com esquemas JSON rígidos, graduação de severidade de avisos (`warn_severity`) e telemetria transparente.

---

## 2. Histórias de Usuário (User Stories)

* **[US1] Desenvolvedor Executando Gates SDD:**  
  Como desenvolvedor operando o ciclo SDD, quero que o `sdd_judge` analise 100% das minhas tarefas atômicas sem cortar o arquivo e me apresente um parecer transparente com cada task auditada, para que eu tenha certeza de que o plano está constitucionalmente seguro antes de codificar.

* **[US2] Desenvolvedor Corrigindo Inconformidades:**  
  Como desenvolvedor que recebeu um aviso ou bloqueio, quero ver a evidência exata da não-conformidade e uma sugestão de correção textual direta (`suggested_fix`), para que eu consiga corrigir o `tasks.md` imediatamente sem adivinhar a regra violada.

* **[US3] Operador em Hardware de Borda (GTX 1060 6GB):**  
  Como desenvolvedor trabalhando localmente com uma placa de 6 GB VRAM, quero que o juiz local utilize modelos compactos de raciocínio dedicados configuráveis via `.env`, para que o gate execute em segundos sem congelar o sistema operacional por estouro de memória.

---

## 3. Requisitos Funcionais (Functional Requirements)

- FR-001: Estrutura Adaptativa de Auditoria por Fase (MUST). O sistema deve fornecer mecanismos especializados de auditoria para cada artefato do ciclo SDD: processamento holístico integral para spec.md, segmentação lógica por seções estruturais para plan.md, e avaliação isolada atômica de cada tarefa para tasks.md, operando em limites de memória compatíveis com hardware de 6 GB de VRAM.

- FR-002: Contratos de Saída Estruturada via JSON Schema (MUST). A inferência do juiz deve utilizar Constrained Grammar Decoding (JSON Schema oficial via parâmetro format no Ollama e responseSchema no Gemini REST), impondo ordem autorregressiva onde critique e evidence precedem verdict, warn_severity e suggested_fix.

- FR-003: Governança e Graduação de Severidade de Avisos (MUST). O veredito de cada item deve classificar a gravidade de WARN em níveis NONE, LOW, MEDIUM e EXTREME. Avisos LOW ou MEDIUM não interrompem o pipeline (exit code 0). Avisos EXTREME devem ser elevados programaticamente para BLOCK (exit code 1).

- FR-004: Varredura Completa com Relatório Consolidado (MUST). No modo tasks, o avaliador deve inspecionar todas as tarefas da lista até a última (T001 a T0N) sem interrupção prematura (sem fail-fast), renderizando ao final uma tabela consolidada com a totalidade dos itens auditados e as sugestões de correção.

- FR-005: Reconciliação Programática Determinística 1:1 (MUST). O código Python deve extrair a lista exata de tarefas declaradas e validar que o conjunto de tarefas auditadas corresponde 1:1 ao conjunto de tarefas extraídas, falhando com erro estrutural caso qualquer item seja omitido.

- FR-006: Matriz Dual de Modelos Locais via Variáveis de Ambiente (P11) (MUST). O provedor local Ollama deve suportar OLLAMA_REASONING_MODEL (default phi4-mini) para fases dedutivas e OLLAMA_CODER_MODEL (default qwen2.5-coder:7b) para fases de código e AST, mantendo compatibilidade com OLLAMA_MODEL.

- FR-007: Observabilidade e Telemetria Transparente (MUST). O cabeçalho de parecer no terminal deve exibir dinamicamente o provedor ativo, o modelo exato e o tempo decorrido no formato '--- PARECER DO JUIZ [{provider}: {model} | {latency}s] ---', sem mensagens estáticas enganosas.


---

## 4. Requisitos Não-Funcionais (Restrições)

* **[NFR-001] Pegada de Memória em Hardware de Borda (P11):**
  * A execução local das fases dedutivas não pode exigir mais de 3.5 GB de VRAM (modelo + contexto), garantindo folga mínima de 2.0 GB para a interface gráfica e o SO na NVIDIA GTX 1060 (6 GB).
* **[NFR-002] Latência e Timeout por Requisição:**
  * No modo 1-a-1 de tarefas, a inferência de cada tarefa no modelo local `phi4-mini` deve completar em menos de 1.5 segundos em hardware equivalente à GTX 1060.
  * O cliente HTTP deve respeitar `OLLAMA_TIMEOUT` (padrão: 30s) e `OLLAMA_CONNECT_TIMEOUT` (padrão: 10s) configurados no `.env`, abortando conexões travadas preventivamente.
* **[NFR-003] Determinismo Sintático:**
  * A taxa de falha de parsing JSON devido a formatação Markdown ou texto espúrio deve ser de 0.0%, garantida pelo constrained decoding nativo do provedor.
* **[NFR-004] Robustez de Infraestrutura (FR-010):**
  * Falhas de conectividade ou indisponibilidade simultânea de provedores devem retornar estritamente `exit code 2` (`INFRA_FAIL`), nunca mascarando falha de rede como rejeição constitucional.

---

## 5. Critérios de Aceite (Acceptance Scenarios)

* **[SC-001] spec.md Avaliado Integralmente sem Cortes:**
  * **Dado** um arquivo `spec.md` contendo User Stories, 5 FRs e cenários Given/When/Then,
  * **Quando** o comando `sdd_judge --mode specify specs/feature/spec.md` é executado,
  * **Então** o modelo recebe o documento integral sem truncamento e emite parecer cobrindo a coerência entre histórias de usuário e requisitos funcionais.

* **[SC-002] plan.md Dividido por Seções Sem Truncamento de 15k:**
  * **Dado** um arquivo `plan.md` com 25.000 caracteres estruturado em 4 seções Markdown (`## `),
  * **Quando** o comando `sdd_judge --mode plan specs/feature/plan.md` é executado,
  * **Então** cada seção é avaliada isoladamente com o cabeçalho contextual compartilhado, sem corte cego de texto.

* **[SC-003] tasks.md em Modo 1-a-1 com Varredura Completa e Suggested Fix:**
  * **Dado** um arquivo `tasks.md` com 15 tarefas atômicas onde a `T002` e a `T009` violam princípios constitucionais,
  * **Quando** o comando `sdd_judge --mode tasks specs/feature/tasks.md` é executado,
  * **Então** todas as 15 tarefas são processadas individualmente, o terminal exibe o relatório consolidado de todas as 15 com o campo `suggested_fix` preenchido com a linha corrigida para `T002` e `T009`, e encerra com `exit code 1`.


* **[SC-004] Elevação de WARN EXTREME para BLOCK:**
  * **Dado** uma tarefa `T004` cuja avaliação retorne `verdict: "WARN"` com `warn_severity: "EXTREME"`,
  * **Quando** o avaliador Python processa o parecer da tarefa,
  * **Então** a tarefa é tratada como impeditiva e o processo finaliza com `exit code 1`.

* **[SC-005] Preservação de WARN LOW/MEDIUM:**
  * **Dado** uma tarefa `T005` cuja avaliação retorne `verdict: "WARN"` com `warn_severity: "LOW"`, e todas as demais `PASS`,
  * **Quando** o avaliador Python processa o parecer da tarefa,
  * **Então** o aviso é impresso em amarelo no terminal e o processo finaliza com `exit code 0`.

* **[SC-006] Telemetria Dinâmica com Fallback Local:**
  * **Dado** que nenhuma chave `GEMINI_API_KEY` está configurada no ambiente e o Ollama está ativo com `phi4-mini`,
  * **Quando** o `sdd_judge` executa uma auditoria,
  * **Então** o banner impresso no terminal é exatamente `--- PARECER DO JUIZ [Ollama: phi4-mini | X.XXs] ---`.

---

## 6. Fora do Escopo (Out of Scope)

* Não inclui substituição do binário do Ollama ou compilação customizada do llama.cpp.
* Não inclui reescrita da suíte de testes de código de negócio de features assistidas.
* Não inclui interface gráfica ou dashboard web para visualização de relatórios do juiz (interface é estritamente CLI/Terminal e logs).

---

## 7. Suposições Verificadas (Grounding P03)

- **Ollama Structured Outputs:** Verificado suporte a `format: <JSON Schema>` via constrained grammar decoding nativo na API oficial do Ollama (`https://ollama.com/blog/structured-outputs` em 12-10-2026).
- **Google Gemini REST API Structured Outputs:** Verificado suporte a `responseSchema` com tipos OpenAPI (`https://ai.google.dev/gemini-api/docs/structured-outputs` em 12-10-2026).
- **Pegada de VRAM do Phi-4 Mini (3.8B):** Verificado que o modelo em quantização Q4_K_M consome ~2.5 GB em pesos e ~0.6 GB em KV cache para 4k tokens, operando com folga na NVIDIA GTX 1060 (6 GB) conforme documentado no [grounding-dossier.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-robustness/grounding-dossier.md).
- **Mitigação de Sycophancy:** Verificado na literatura científica (Arxiv 2308.03958) que a geração de evidência/crítica antes do veredito reduz falsos positivos em até 72%.
- **Degradação Lost-in-the-Middle:** Verificado na literatura científica (Arxiv 2307.03172) que fatiamento atômico previne perda de foco no meio de sequências longas.
