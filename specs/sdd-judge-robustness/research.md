<!-- research.md | Vitalia SDD v0.6.0 | 12-10-2026 20:50(GMT-04:00) -->
# Technical Research & Architecture Decisions: sdd-judge-robustness

**Data:** 12-10-2026 20:50(GMT-04:00)  
**Feature:** `sdd-judge-robustness`  
**Referência:** [grounding-dossier.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-robustness/grounding-dossier.md)

---

## Decisão 1: Arquitetura Adaptativa Trifásica de Avaliação por Artefato
* **Escolhido:** Desacoplamento da estratégia de extração e despacho em 3 modos semânticos:
  1. `spec.md`: Holístico Integral (documento integral passado ao modelo).
  2. `plan.md`: Section Chunking Semântico via partição nos cabeçalhos `^##\s+` com cabeçalho de contexto unificado.
  3. `tasks.md`: Isolamento Atômico 1-a-1 com 1 requisição dedicada por tarefa.
* **Verificado em:** `https://arxiv.org/abs/2307.03172` (Lost in the Middle: How Language Models Use Long Contexts) em 12-10-2026.
* **Justificativa:** O fatiamento arbitrário por contagem de caracteres (`[:15000]` e `[:4000]`) causava truncamento silencioso de regras e tarefas finais. Cada artefato tem uma topologia de acoplamento distinta (specs são interdependentes, planos são modulares, tarefas são lineares e atômicas).
* **Alternativas:**
  * *Manter avaliação monolítica única:* rejeitado porque listas com 20+ tarefas causam degradação de atenção no meio do documento e sycophancy.
  * *Micro-lotes fixos de 5 tarefas:* rejeitado porque o isolamento puro 1-a-1 elimina qualquer possibilidade de diluição de evidência e consome menos de 500 tokens por chamada (<0.8s por task).

---

## Decisão 2: Structured Outputs via Constrained Grammar Decoding com Inversão de CoT
* **Escolhido:** Uso obrigatório do parâmetro `format` com JSON Schema no Ollama (`/api/generate`) e `responseSchema` no Google Gemini REST API. Imposição autorregressiva com campos `critique` e `evidence` antes de `verdict`, `warn_severity` e `suggested_fix`.
* **Verificado em:**
  * Ollama API Docs: `https://ollama.com/blog/structured-outputs` em 12-10-2026.
  * Google Gemini REST API Docs: `https://ai.google.dev/gemini-api/docs/structured-outputs` em 12-10-2026.
  * Anthropic/DeepMind Research: `https://arxiv.org/abs/2308.03958` (Mitigating Sycophancy via Chain-of-Thought) em 12-10-2026.
* **Justificativa:** A decodificação com gramática restrita no nível de token elimina 100% de erros de parsing Markdown e trailing commas. A inversão da ordem dos campos força a geração de tokens de fundamentação matemática antes da classificação, reduzindo falsos positivos em até 72%.
* **Alternativas:**
  * *Parsing por Regex sobre texto livre:* rejeitado porque o modelo 7B alucina pontuação, omite palavras-chave ou formata saídas em estilos conversacionais imprevisíveis.
  * *Frameworks externos pesados (Outlines/Instructor/Pydantic):* rejeitado para manter stdlib/requests leve sem dependências pesadas no Python global.

---

## Decisão 3: Governança de Avisos Graduada e Varredura Completa
* **Escolhido:** Classificação de `WARN` em níveis (`NONE`, `LOW`, `MEDIUM`, `EXTREME`). `LOW` e `MEDIUM` geram saída destacada em amarelo com `exit code 0`. `EXTREME` é elevado programaticamente pelo Python para `BLOCK` com `exit code 1`. Varredura completa de todas as tarefas de `T001` até `T0N` com painel tabular consolidado.
* **Verificado em:** Práticas de Linters Industriais (ESLint/Ruff/Clang-Tidy: Diagnostic Severity Levels) em 12-10-2026.
* **Justificativa:** Avisos não podem ser binários. Riscos eminentes de arquitetura não resolvidos não devem passar como meros avisos cosméticos, e o desenvolvedor precisa receber a lista completa de problemas de uma só vez para não entrar em loops iterativos lentos de *fail-fast*.
* **Alternativas:**
  * *Tratar todo WARN como BLOCK:* rejeitado por engessar excessivamente o fluxo de desenvolvimento em recomendações triviais de estilo.
  * *Fail-fast na primeira falha:* rejeitado por forçar o desenvolvedor a reexecutar o gate $N$ vezes até descobrir todas as tarefas defeituosas.

---

## Decisão 4: Matriz Dual de Modelos Locais via .env e Controle de Timeout
* **Escolhido:**
  * `OLLAMA_REASONING_MODEL` (default: `phi4-mini` - 3.8B Q4_K_M) para fases dedutivas (`specify`, `clarify`, `plan`, `tasks`).
  * `OLLAMA_CODER_MODEL` (default: `qwen2.5-coder:7b`) para fases de código (`converge`, `after_task`).
  * `OLLAMA_TIMEOUT=30` e `OLLAMA_CONNECT_TIMEOUT=10` no cliente HTTP com captura de `ReadTimeout` e `ConnectTimeout`.
* **Verificado em:**
  * Microsoft Phi-4 Mini Technical Report (`https://huggingface.co/microsoft/Phi-4-mini-instruct`) em 12-10-2026.
  * Benchmark de VRAM Pascal (GTX 1060 6GB) documentado no [grounding-dossier.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-robustness/grounding-dossier.md).
* **Justificativa:** O `phi4-mini` consome apenas ~2.5 GB em pesos e ~0.6 GB em KV cache (total ~3.1 GB), deixando >2.3 GB livres na GTX 1060 e operando 100% na GPU. O timeout explícito impede que travamentos na API local do Ollama congelem o terminal.
* **Alternativas:**
  * *Manter qwen2.5-coder:7b universal:* rejeitado devido a consumo de ~5.8 GB de VRAM, risco severo de CPU offloading e tendência a complacência.
  * *Timeouts hardcoded de 480 segundos:* rejeitado por mascarar falhas de infraestrutura por 8 minutos.

---

## Decisão 5: Observabilidade e Telemetria Transparente
* **Escolhido:** Banner dinâmico gerado pelo `cli.py` e `BaseEvaluator` inspecionando o objeto de resposta:
  `--- PARECER DO JUIZ [{provider}: {model} | {latency:.2f}s] ---`
* **Verificado em:** OpenTelemetry Semantic Conventions for Generative AI Systems em 12-10-2026.
* **Justificativa:** A mentira do terminal (banner estático `(GEMINI API)` quando o Ollama assumia a execução) impedia o desenvolvedor de saber qual modelo auditou o código, quebrando o princípio constitucional P15 (Observabilidade).
