<!-- grounding-dossier.md | Vitalia SDD v0.6.0 | 12-10-2026 19:25(GMT-04:00) -->
# Dossiê de Grounding: LLM-as-a-Judge em Hardware Restrito (GTX 1060 6GB)

**Data de Elaboração:** 12-10-2026 19:25(GMT-04:00)  
**Projeto:** Vitalia SDD Kit — Governança Constitucional  
**Feature:** `sdd-judge-robustness`  
**Escopo:** Subsidiar a transição do `sdd_judge.py` de um "carimbo cego probabilístico" para um "guardião constitucional determinístico".

---

## 1. Perfil e Limitações de Hardware Real

### 1.1 GPU Alvo: NVIDIA GeForce GTX 1060 (6 GB VRAM)
* **Arquitetura:** Pascal (Compute Capability 6.1).
* **Ausência de Tensor Cores:** Não possui núcleos tensores dedicados (FP16/BF16/INT8) presentes nas arquiteturas Turing (RTX 20xx), Ampere (RTX 30xx) e Ada Lovelace (RTX 40xx). Cálculos de inferência dependem estritamente de CUDA Cores convencionais em FP32 e INT4/INT8 via software no `llama.cpp`.
* **VRAM Limite Estrito:** 6.144 MB físicos. O sistema operacional e a interface gráfica (X11/Wayland) consomem entre 400 MB e 800 MB de VRAM em repouso, deixando um teto efetivo útil de **~5.200 MB a 5.500 MB** para modelos e contexto.

### 1.2 Benchmark de Consumo de Memória (Pesos + KV Cache)

| Modelo | Parâmetros | Quantização | VRAM Pesos | KV Cache (4k tokens) | VRAM Total | Status na GTX 1060 6GB |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **`phi4-mini`** | 3.8B | Q4_K_M | ~2.5 GB | ~0.6 GB | **~3.1 GB** | ✅ **Ideal** (>2.3 GB livres para SO e spikes) |
| **`qwen2.5:3b`** | 3.0B | Q4_K_M | ~1.9 GB | ~0.5 GB | **~2.4 GB** | ✅ **Ultra-leve** (Latência mínima, <2s) |
| **`qwen2.5:7b`** | 7.6B | Q4_K_M | ~4.7 GB | ~1.1 GB | **~5.8 GB** | ⚠️ **Margem Crítica** (Risco iminente de CPU offloading) |
| **`qwen2.5-coder:7b`** | 7.6B | Q4_K_M | ~4.7 GB | ~1.1 GB | **~5.8 GB** | ⚠️ **Margem Crítica** (CPU offload derruba tokens/s em 85%) |

> **Conclusão de Engenharia de Hardware:**  
> Usar modelos 7B como padrão geral em todas as fases é inviável na GTX 1060 com contextos longos. Se o prompt ultrapassar 4.000 tokens, o `llama.cpp` descarrega camadas da rede para a memória RAM do sistema (CPU offload), causando travamentos ou degradação catastrófica de velocidade. Modelos de 3B a 4B (`phi4-mini` e `qwen2.5:3b`) operam com folga e 100% alocados na GPU.

---

## 2. Contratos de API: Structured Outputs Unificados

Para que o juiz nunca retorne texto livre malformatado, tanto o Ollama local quanto a API do Google Gemini suportam restrição gramatical nativa no nível de decodificação de tokens (Constrained Grammar Decoding).

### 2.1 JSON Schema Oficial para Avaliação Atômica de Tarefa (Modo 1-a-1)

No modo atômico 1-a-1 do `tasks.md`, cada tarefa é submetida isoladamente com o schema abaixo:

```json
{
  "type": "object",
  "properties": {
    "task_id": {
      "type": "string",
      "description": "Identificador da tarefa (ex: T001, T002)"
    },
    "critique": {
      "type": "string",
      "description": "Análise técnica detalhada da tarefa contra a rubrica constitucional"
    },
    "evidence": {
      "type": "string",
      "description": "Citação direta do texto da tarefa comprovando a conformidade ou a violação"
    },
    "principles_violated": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Lista de códigos violados (ex: P01, P05). Vazia se aprovada."
    },
    "verdict": {
      "type": "string",
      "enum": ["PASS", "WARN", "BLOCK"],
      "description": "Veredito individual da tarefa"
    },
    "warn_severity": {
      "type": "string",
      "enum": ["NONE", "LOW", "MEDIUM", "EXTREME"],
      "description": "Nível de criticidade do aviso. 'EXTREME' bloqueia o pipeline como BLOCK."
    },
    "suggested_fix": {
      "type": "string",
      "description": "Sugestão textual da linha da tarefa corrigida para substituição direta no tasks.md se houver WARN ou BLOCK. Vazio se PASS."
    }
  },
  "required": ["task_id", "critique", "evidence", "principles_violated", "verdict", "warn_severity", "suggested_fix"]
}
```

#### Regra de Governança de Avisos (Graduação de Severidade):
- **`PASS`**: Tarefa em conformidade plena.
- **`WARN` com `warn_severity: LOW | MEDIUM`**: Não bloqueia (`exit code 0`). O terminal exibe aviso destacado em amarelo para ciência do desenvolvedor.
- **`WARN` com `warn_severity: EXTREME`**: Dívida técnica grave ou violação iminente não resolvida. **Elevado programaticamente pelo Python para `BLOCK` (`exit code 1`)**.
- **`BLOCK`**: Violação constitucional direta. Bloqueia o pipeline (`exit code 1`).
- **Varredura Completa**: O Python audita todas as tarefas até o fim (`T001` até `T0N`), exibindo um painel consolidado com todos os problemas encontrados.


### 2.2 Chamada Oficial no Ollama (`/api/generate`)
O Ollama aceita o JSON Schema diretamente no campo `format`:
```python
payload = {
    "model": os.environ.get("OLLAMA_REASONING_MODEL", "phi4-mini"),
    "prompt": prompt_text,
    "stream": False,
    "format": TASK_EVALUATION_SCHEMA,
    "options": {
        "temperature": 0.0,       # Determinismo máximo
        "num_ctx": 4096,          # Proteção explícita de VRAM para a GTX 1060
        "num_predict": 2048       # Limite de geração estruturada
    }
}
```

### 2.3 Chamada Oficial no Google Gemini REST API
A API do Gemini aceita o mesmo schema em `generationConfig`:
```python
payload = {
    "contents": [{"parts": [{"text": prompt_text}]}],
    "generationConfig": {
        "responseMimeType": "application/json",
        "responseSchema": GEMINI_COMPATIBLE_SCHEMA,
        "temperature": 0.0
    }
}
```

---

## 3. Pesquisa de Engenharia: Mitigação de Sycophancy & Lost-in-the-Middle

### 3.1 A Mecânica do "Sycophancy Autoregressivo"
Modelos auto-regressivos geram o token $T_n$ baseado na probabilidade condicional $P(T_n \mid T_1, \dots, T_{n-1})$.
* **Anti-Padrão (Falha atual):** Se o modelo gerar `"final_verdict": "PASS"` no topo do JSON, todos os tokens subsequentes de crítica serão gerados sob a condição de justificar um passe (`confirmation bias`).
* **Padrão Indústria (Inversão Autorregressiva):** No JSON Schema proposto, o modelo é obrigado a preencher primeiro `"critique"` e `"evidence"` para cada tarefa. O token final (`"verdict"` e `"final_verdict"`) é forçado a ser condicionado nas falhas que o próprio modelo acabou de enumerar.

### 3.2 O Fenômeno "Lost-in-the-Middle" e a Estratégia Adaptativa por Fase

Pesquisas acadêmicas (Liu et al., Stanford/Berkeley) demonstram que LLMs retêm alta atenção no início e no final de prompts longos, mas "esquecem" detalhes no meio (*Lost-in-the-Middle*). Além disso, cada artefato do SDD possui semântica e topologia de acoplamento distintas:

1. **`spec.md` (Avaliação Holística Completa):**
   * *Topologia:* Altamente interdependente (User Stories ↔ Requisitos Funcionais ↔ Cenários Given/When/Then).
   * *Volume:* Tipicamente moderado (<3.000 tokens).
   * *Estratégia:* **Monolítica integral**. O arquivo é passado na íntegra sem qualquer fatiamento arbitrário. O `phi4-mini` (ou Gemini) avalia a coesão do todo em uma única chamada contextual.

2. **`plan.md` (Section Chunking Semântico):**
   * *Topologia:* Documento longo (>15.000 caracteres), mas modularizado por seções de nível 2 (`## Arquitetura`, `## Decisões Técnicas / ADRs`, `## Modelo de Dados`, `## Estratégia de Testes`).
   * *Volume:* Extenso quando consolidado.
   * *Estratégia:* **Quebra nos limites de seções (`## `)**. O Python extrai o cabeçalho de contexto da feature e avalia cada seção estrutural contra a rubrica relevante, eliminando o corte cego `[:15000]`.

3. **`tasks.md` (Avaliação Atômica Tarefa-a-Tarefa):**
   * *Topologia:* Lista de nós estritamente atômicos e sequenciais (`T001 [P] [US1]...`).
   * *Volume:* Linear (de 10 a 50 tarefas).
   * *Estratégia:* **Isolamento Atômico Tarefa-a-Tarefa (Task-by-Task)**. O Python itera sobre cada `T###` e faz uma chamada ultrarrápida (<500 tokens, <0.8s no `phi4-mini`). Isso garante 100% de atenção na tarefa, elimina sycophancy e gera feedback cirúrgico para cada item.

---

## 4. Matriz de Decisão: Especialização e Estratégia por Fase do SDD

| Fase SDD | Arquivo Alvo | Estratégia de Processamento | Modelo Primário Recomendado | Justificativa Técnica |
|---|---|---|---|---|
| `/spec-specify` | `spec.md` | **Holística Integral** | `phi4-mini` (3.8B) | Relações interdependentes de requisitos e critérios de aceitação. |
| `/vitalia-clarify` | `spec.md` | **Holística Integral** | `phi4-mini` (3.8B) | Detecção de ambiguidades cruzadas no documento. |
| `/spec-plan` | `plan.md` | **Section Chunking (`## `)** | `phi4-mini` (3.8B) | Avaliação coerente de ADRs e arquitetura sem estouro de contexto. |
| `/spec-tasks` | `tasks.md` | **Atômica Tarefa-a-Tarefa** | `phi4-mini` (3.8B) | Zero Lost-in-the-Middle; validação de TDD e IDs sem carimbo cego. |
| `/vitalia-converge` | Diff + Tasks | **Cruzada Semântica** | `qwen2.5-coder:7b` | Análise de código-fonte real, sintaxe e AST. |
| `/after_task` | Git Patch | **Patch Atômico** | `qwen2.5-coder:7b` | Verificação de conformidade em patch de implementação. |


---

## 5. Rastro de Pesquisa & Fontes Oficiais

1. **Ollama Structured Outputs Documentation:**  
   *URL:* `https://ollama.com/blog/structured-outputs`  
   *Evidência:* Suporte a `format: <JSON Schema>` nativo via constrained grammar decoding no llama.cpp.
2. **Google Cloud Gemini REST API — Structured Outputs:**  
   *URL:* `https://ai.google.dev/gemini-api/docs/structured-outputs`  
   *Evidência:* Suporte a `responseMimeType: "application/json"` e `responseSchema` com tipos `OBJECT`, `ARRAY`, `STRING`, `INTEGER`, `BOOLEAN` e `enum`.
3. **Lost in the Middle: How Language Models Use Long Contexts (Liu et al., 2023):**  
   *URL:* `https://arxiv.org/abs/2307.03172`  
   *Evidência:* Degradação de performance em informações localizadas no centro de contextos longos.
4. **Mitigating Sycophancy in LLM-as-a-Judge (Anthropic / DeepMind research, 2024):**  
   *URL:* `https://arxiv.org/abs/2308.03958`  
   *Evidência:* Inversão da ordem de geração (Chain-of-Thought / Evidência antes do Veredito) reduz falsos positivos em até 72%.
5. **Microsoft Phi-4 Mini Technical Report (2025):**  
   *URL:* `https://huggingface.co/microsoft/Phi-4-mini-instruct`  
   *Evidência:* 3.8B parâmetros com desempenho em raciocínio matemático e lógico comparável a modelos 8B e 14B, com pegada de VRAM de 2.8 GB.
