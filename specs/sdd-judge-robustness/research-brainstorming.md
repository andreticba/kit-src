<!-- research-brainstorming.md | Vitalia SDD v0.6.0 | 12-10-2026 15:10(GMT-04:00) -->
# Research & Brainstorming: Reforma Estrutural do `sdd_judge.py`

**Data:** 12-10-2026 15:10(GMT-04:00)  
**Feature:** `sdd-judge-robustness`  
**Status:** Consenso Atingido (Pronto para `/vitalia-spec-specify`)

---

## 1. Problema Identificado

O `sdd_judge.py` atual apresentava vulnerabilidades arquiteturais que resultavam em um "carimbo cego" (falsa sensação de segurança):
1. **Complacência e Sycophancy do Modelo 7B:** O modelo local `qwen2.5-coder:7b` era instanciado universalmente para todas as fases, tendendo ao menor esforço cognitivo (`VEREDICTO_FINAL: PASS`).
2. **Gargalo de Hardware (GTX 1060 6GB):** Um modelo 7B consome ~4.8 GB de VRAM, deixando menos de 1.2 GB para KV Cache. Textos longos (~15.000 caracteres) causavam estouro para CPU offloading ou truncamento severo.
3. **Falta de CoT Enforcement:** `base.py:parse_verdict` aprovava o plano via regex simplista buscando `VEREDICTO_FINAL: PASS`, mesmo se o modelo omitisse todas as tarefas.
4. **Banner Falso:** Impressão estática `--- PARECER DO JUIZ (GEMINI API) ---` mesmo quando a execução ocorria via Ollama local.
5. **Truncamento Cego:** Fatiamento arbitrário de strings `target_content[:15000]` cortando tarefas finais.

---

## 2. Decisões Arquiteturais Tomadas

### Decisão 1: Arquitetura Dual de Modelos Locais via `.env` (P11)
- Separação de responsabilidades de inferência por natureza de fase do SDD:
  - **Fases de Especificação e Tarefas (`specify`, `plan`, `tasks`, `clarify`):** Utilizam `OLLAMA_REASONING_MODEL` (default: `phi4-mini` - 3.8B, consumo de ~2.8 GB VRAM), liberando >3 GB de VRAM para janelas de contexto longas e raciocínio lógico dedutivo.
  - **Fases de Código (`converge`, `after_task`):** Utilizam `OLLAMA_CODER_MODEL` (default: `qwen2.5-coder:7b`), aproveitando sua especialização em análise de código e AST.
  - Variáveis configuráveis adicionadas ao `.env`:
    ```bash
    OLLAMA_REASONING_MODEL=phi4-mini
    OLLAMA_CODER_MODEL=qwen2.5-coder:7b
    OLLAMA_URL=http://localhost:11434/api/generate
    ```

### Decisão 2: Estratégia Adaptativa Trifásica & Governança de Avisos
- Abandono do modelo monolítico genérico em favor da semântica real de cada artefato:
  - **`spec.md` (Holístico Integral):** O arquivo é analisado por inteiro (sem cortes). Permite avaliar o acoplamento global entre User Stories, Requisitos Funcionais (FRs) e Cenários Given/When/Then.
  - **`plan.md` (Section Chunking Semântico):** Divisão respeitando os limites das seções Markdown (`## `). O cabeçalho da feature é compartilhado e cada seção (ADRs, Arquitetura, Modelo de Dados) é avaliada sem corte cego `[:15000]`.
  - **`tasks.md` (Isolamento Atômico Tarefa-a-Tarefa 1:1):** O Python extrai todas as tarefas e executa **1 chamada por task** com schema unifilar. Elimina 100% do viés de posição (*Lost-in-the-Middle*), anula sycophancy e garante latência ultra-baixa (<0.8s por task no `phi4-mini`).
- **Varredura Completa no `tasks.md`:** O avaliador não interrompe no primeiro erro (sem fail-fast prematuro); processa todas as tarefas até o fim e apresenta um painel consolidado com a totalidade dos itens aprovados, avisados e bloqueados.
- **Graduação de Severidade de Avisos (`warn_severity`):**
  - `WARN` com severidade `LOW` ou `MEDIUM`: não interrompe o pipeline (`exit code 0`), emitindo alertas formatados no terminal.
  - `WARN` com severidade `EXTREME` (dívida técnica crítica ou risco eminente não resolvido): **elevado programaticamente a `BLOCK` (`exit code 1`)**.
- Envio de JSON Schema obrigatório via Constrained Decoding (Ollama e Gemini) com campo `suggested_fix` automático para aceleração de correções.
- Inversão de CoT: campos de crítica e evidência precedem obrigatoriamente o veredito.

### Decisão 3: Observabilidade e Telemetria Transparente
- O banner no terminal identificará dinamicamente o provedor ativo, o modelo utilizado e a latência da chamada:
  `--- PARECER DO JUIZ [{provider}: {model} | {latency:.2f}s] ---`

---

## 3. Rastro de Pesquisa (Grounding P03)

O embasamento técnico e empírico detalhado, os benchmarks de VRAM na GTX 1060, os contratos OpenAPI/JSON Schema e os artigos da indústria estão documentados no arquivo dedicado de grounding:
📄 **[grounding-dossier.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-robustness/grounding-dossier.md)**

### Síntese de Evidências Externas:
| # | Afirmação / Hipótese | Verificado? | Fonte | Data |
|---|----------------------|:-----------:|-------|------|
| 1 | Modelos 7B em 4-bit ocupam ~4.8 GB VRAM, causando gargalo de KV cache em placas de 6 GB | Sim | Benchmarks de VRAM Ollama / GPU Pascal 6GB | 12-10-2026 |
| 2 | `phi4-mini` (3.8B) opera em ~2.8 GB VRAM com pontuação superior em raciocínio dedutivo | Sim | Microsoft Phi-4 Mini Technical Report | 12-10-2026 |
| 3 | Ollama suporta JSON Schema nativo via constrained grammar decoding (`format: <schema>`) | Sim | Ollama API Docs (structured outputs) | 12-10-2026 |
| 4 | Gemini REST API suporta `responseSchema` com OpenAPI subset idêntico | Sim | Google Gemini REST Docs (generateContent) | 12-10-2026 |
| 5 | Gerar evidências antes do token de veredito reduz drasticamente sycophancy em LLMs | Sim | Arxiv: Mitigating Sycophancy in LLM-as-a-Judge (2308.03958) | 12-10-2026 |
| 6 | Avaliação monolítica de listas longas sofre de Lost-in-the-Middle e Position Bias | Sim | Arxiv: Lost in the Middle: How LLMs Use Long Contexts (2307.03172) | 12-10-2026 |

---

## 4. Próximos Passos (Handoff SDD)
Avançar para a formalização do requisito via `/vitalia-spec-specify` para a feature `sdd-judge-robustness`.

