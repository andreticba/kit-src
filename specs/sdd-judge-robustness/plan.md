<!-- plan.md | Vitalia SDD v0.6.0 | 12-10-2026 20:53(GMT-04:00) -->
# Implementation Plan: Reforma Estrutural do SDD Judge (Juiz Constitucional Robusto)

**Branch**: `sdd-judge-robustness` | **Date**: 12-10-2026 20:53(GMT-04:00) | **Spec**: [spec.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-robustness/spec.md)

---

## 1. Summary

Reforma arquitetural do componente `sdd_judge` (guardião constitucional do Vitalia SDD Kit), eliminando a complacência e o sycophancy por meio de:
1. **Auditoria Adaptativa por Fase:** Estratégia holística para `spec.md`, section chunking em limites `## ` para `plan.md`, e isolamento atômico 1-a-1 com varredura completa para `tasks.md`.
2. **Structured Outputs com Inversão de CoT:** Constrained Grammar Decoding nativo (JSON Schema) onde os campos `critique` e `evidence` precedem autorregressivamente `verdict`, `warn_severity` e `suggested_fix`.
3. **Governança Graduada de Avisos:** Classificação de `WARN` em níveis (`NONE`, `LOW`, `MEDIUM`, `EXTREME`), onde `EXTREME` é promovido programaticamente para `BLOCK` (`exit code 1`).
4. **Matriz Dual de Modelos e Otimização para Borda (GTX 1060 6GB):** Roteamento via `.env` de `phi4-mini` (3.8B Q4_K_M, ~3.1 GB VRAM) para tarefas dedutivas e `qwen2.5-coder:7b` para código, com controle estrito de timeouts HTTP.
5. **Telemetria Transparente:** Remoção de banners estáticos enganosos e inclusão de métricas reais de provedor, modelo e latência em segundos.

---

## 2. Technical Context

* **Language/Version:** Python 3.10+ (compatível com 3.10, 3.11, 3.12, 3.14).
* **Primary Dependencies:** `requests` (cliente HTTP para Ollama e Gemini REST), `pyyaml` (carregamento de constituição e perfis do kit), biblioteca padrão (`json`, `re`, `os`, `sys`, `pathlib`, `typing`, `time`, `dataclasses`).
* **Storage:** N/A (arquivos de especificação Markdown e schemas JSON em disco).
* **Testing:** Pytest / Scripts de validação de regressão CLI descritos no [quickstart.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-robustness/quickstart.md).
* **Target Platform:** Linux / WSL2 (Ubuntu no ambiente `ai-control`), hardware de borda NVIDIA GTX 1060 6GB.
* **Project Type:** CLI Tool & Lifecycle Hooks para SDD Kit.
* **Performance Goals:**
  * Inferência de cada task individual no `phi4-mini` em hardware GTX 1060 < 1.5s (SC-003, NFR-002).
  * Consumo máximo de VRAM nas fases dedutivas $\le 3.5\text{ GB}$ (NFR-001).
  * 0.0% de falha de parsing JSON por markdown espúrio via constrained decoding nativo (NFR-003).
* **Constraints:**
  * Não quebrar compatibilidade da CLI `sdd_judge.py --mode <mode> <path>`.
  * Nenhum modelo ou segredo hardcoded no código-fonte Python (Princípios P06 e P11).
  * Preservar carimbo imutável `America/Cuiaba (GMT-04:00)` em todos os cabeçalhos (Princípio P04).

---

## 3. Constitution Check (Auditoria Constitucional pelo Agente)

Como Juiz Constitucional designado para este ciclo, realizo a auditoria pré-implementação do plano técnico contra a Constituição do Vitalia Kit:

| Princípio | Descrição | Status | Evidência / Justificativa no Plano |
| :--- | :--- | :---: | :--- |
| **P00 (Purpose Arbiter)** | Bem-estar humano & rigor técnico | **PASS** | Protege o desenvolvedor contra falsas aprovações de planos defeituosos e evita congelamento do sistema operacional na GPU local. |
| **P01 (SDD Pipeline Inviolability)** | Fluxo specify → plan → tasks → implement | **PASS** | O plano deriva estritamente de `spec.md` aprovado e estabelece as bases para o `tasks.md`. |
| **P02 (User-Centric Validation)** | Impacto e valor para o usuário final | **PASS** | Apresenta relatórios tabulares completos com `suggested_fix` textual pronto para aplicação. |
| **P03 (External Verification)** | Grounding com fontes autoritativas | **PASS** | Todas as decisões arquiteturais foram fundamentadas em documentação oficial e artigos científicos documentados no `research.md`. |
| **P04 (Timestamp GMT-04:00)** | Fuso America/Cuiaba no cabeçalho | **PASS** | Cabeçalho canônico presente em todos os artefatos `spec.md`, `research.md`, `plan.md` e schemas. |
| **P06 (Secrets Never in Git)** | Chaves e credenciais fora do versionamento | **PASS** | `GEMINI_API_KEY` consumida exclusivamente de `os.environ`; `.env` já atualizado e protegido. |
| **P11 (Hardware Agnosticism)** | Sem modelo hardcoded, suporte a borda | **PASS** | Modelos obtidos via `os.environ` (`OLLAMA_REASONING_MODEL`, `OLLAMA_CODER_MODEL`), footprint <3.5 GB VRAM na GTX 1060. |
| **P15 (Observabilidade & Logging)** | Telemetria e logs transparentes | **PASS** | Cabeçalho dinâmico `--- PARECER DO JUIZ [{provider}: {model} \| {latency}s] ---` sem ilusão de observabilidade. |
| **P16 (Artifact Integrity & Mermaid)** | Integridade sem regressão | **PASS** | Contratos de schema JSON rígidos sem alterações destrutivas em pipelines existentes. |

**Veredicto Constitucional:** **APROVADO (PASS)** — O plano atende integralmente a todas as cláusulas constitucionais.

---

## 4. Technical Decisions

As decisões técnicas foram formalizadas no documento [research.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-robustness/research.md):
* **ADR-01:** Abordagem Adaptativa Trifásica (Holística para `spec.md`, Section Chunking `## ` para `plan.md`, 1-a-1 Atômico com Varredura Total para `tasks.md`).
* **ADR-02:** Structured Outputs via JSON Schema com ordem autorregressiva invertida (`critique` $\to$ `evidence` $\to$ `verdict` $\to$ `warn_severity` $\to$ `suggested_fix`).
* **ADR-03:** Governança Graduada de Avisos (`WARN EXTREME` $\to$ `BLOCK`) e Varredura Completa sem fail-fast prematuro.
* **ADR-04:** Matriz Dual de Modelos Locais via `.env` (`phi4-mini` para raciocínio, `qwen2.5-coder:7b` para código) com timeouts de 30s/10s.
* **ADR-05:** Telemetria Dinâmica com banner inspecionando o provedor e modelo reais da inferência.

---

## 5. Project Structure

### 5.1 Documentation & Feature Artifacts
```text
specs/sdd-judge-robustness/
├── checklists/
│   └── requirements.md            # Checklist de requisitos aprovado
├── contracts/
│   ├── task_eval_schema.json      # Contrato JSON Schema para avaliação 1-a-1 de tasks
│   └── section_eval_schema.json   # Contrato JSON Schema para seções e documentos
├── grounding-dossier.md           # Dossiê de hardware da GTX 1060 e papers científicos
├── research-brainstorming.md      # Registro socrático de decisões
├── research.md                    # ADRs consolidadas da Fase 0
├── spec.md                        # Especificação funcional formal (FR-001 a FR-007)
├── plan.md                        # Este plano técnico de implementação
└── quickstart.md                  # Roteiro de validação end-to-end
```

### 5.2 Source Code Affected (Master em `source/` e Deploy em `~/.vitalia/`)
```text
source/src/hooks/sdd_judge/
├── __init__.py                    # Inicialização e exports públicos do pacote
├── cli.py                         # Ponto de entrada CLI, captura de argumentos e banner dinâmico
├── providers/
│   ├── base.py                    # Classe abstrata LLMProvider e dataclass LLMResponse
│   ├── ollama.py                  # Provedor Ollama com JSON format schema, timeout e latência
│   └── gemini.py                  # Provedor Gemini REST com responseSchema e medição de latência
├── evaluators/
│   ├── base.py                    # BaseEvaluator com parsing de JSON Schema e severidade de WARN
│   ├── specify.py                 # Evaluator holístico integral de spec.md (sem truncamento de 4k)
│   ├── plan.py                    # Evaluator particionado por seções ## sem corte de 15k
│   └── tasks.py                   # Evaluator atômico 1-a-1 com varredura completa e tabela consolidada
└── prompts/
    └── system_prompts.py          # Prompts de sistema com CoT invertido e rubricas constitucionais
```

---

## 6. Phase Overview

### Phase 1: Setup & Data Contracts
* Configurar e validar contratos JSON Schema oficiais em `source/src/hooks/sdd_judge/contracts/` ou embutidos no código.
* Definir dataclass `LLMResponse(content: str, provider: str, model: str, latency: float, status_code: int)`.
* Atualizar `.env` com as variáveis padrão e garantir leitura resiliente via `os.environ`.

### Phase 2: Providers Refactor (Ollama & Gemini)
* Refatorar `OllamaProvider`:
  * Adicionar suporte ao parâmetro `format` recebendo dicionário de JSON Schema.
  * Implementar suporte a `OLLAMA_REASONING_MODEL` e `OLLAMA_CODER_MODEL`.
  * Configurar `timeout=(connect_timeout, read_timeout)` usando `OLLAMA_CONNECT_TIMEOUT` (10s) e `OLLAMA_TIMEOUT` (30s).
  * Retornar instância de `LLMResponse` com métricas reais de execução.
* Refatorar `GeminiProvider`:
  * Adicionar suporte a `generationConfig.responseSchema` no payload REST.
  * Retornar instância de `LLMResponse` com métricas reais de execução.

### Phase 3: Evaluators Refactor & Inverted CoT
* Refatorar `BaseEvaluator`:
  * Implementar `parse_structured_evaluation(response: LLMResponse, schema_type: str)`.
  * Implementar normalização de veredito: elevação de `WARN` com `warn_severity == 'EXTREME'` para `exit code 1` (BLOCK).
* Refatorar `SpecifyEvaluator`:
  * Remover truncamento arbitrário `[:4000]`.
  * Avaliar coerência holística integral de `spec.md` com `section_eval_schema.json`.
* Refatorar `PlanEvaluator`:
  * Remover truncamento arbitrário `[:15000]`.
  * Implementar particionamento do Markdown em blocos `## ` (seções), preservando cabeçalho compartilhado.
  * Avaliar cada seção contra a rubrica constitucional.
* Refatorar `TasksEvaluator`:
  * Implementar parser que isola cada task `T001`, `T002`, ..., `T0N`.
  * Validar correspondência determinística 1:1 entre tarefas extraídas e tarefas declaradas.
  * Executar varredura completa atômica (1 requisição por task) usando `task_eval_schema.json`.
  * Renderizar tabela consolidada com colunas: `[Task ID] | [Veredicto] | [Severidade] | [Princípio] | [Suggested Fix]`.

### Phase 4: CLI & Telemetry Transparency
* Refatorar `cli.py`:
  * Substituir cabeçalho estático pelo banner dinâmico:
    `--- PARECER DO JUIZ [{provider}: {model} | {latency:.2f}s] ---`.
  * Exibir sumário de execução e códigos de saída padronizados (`0` = PASS / WARN aceito, `1` = BLOCK / WARN extremo, `2` = falha de infraestrutura).

### Phase 5: Verification & Synchronization
* Executar cenários do [quickstart.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-robustness/quickstart.md) para validar `spec.md`, `plan.md` e `tasks.md`.
* Sincronizar código-fonte do mestre para a instalação do kit: `rsync -av source/ ~/.vitalia/`.
* Testar `python3 ~/.vitalia/src/hooks/sdd_judge.py --mode tasks` em lote com GPU real.

---

## 7. Critérios de Conclusão do Plano

- [x] Contexto técnico, limites de VRAM e dependências documentados.
- [x] Constitution Check realizado e aprovado pelo Juiz Constitucional.
- [x] Decisões técnicas mapeadas com referência direta a `research.md`.
- [x] Estrutura de arquivos em `source/` mapeada com precisão.
- [x] Fases de implementação sequenciadas para guiar `/vitalia-spec-tasks`.
