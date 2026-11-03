<!-- sdd-session-briefing.md | Vitalia SPEC Kit v0.0.1 | 02-11-2026 20:30(GMT-04:00) -->
> **sdd-session-briefing.md | Vitalia SPEC Kit v0.0.1 | 02-11-2026 20:30(GMT-04:00)**

# Documento de Transição e Briefing Operacional: Vitalia SPEC Kit (v0.0.1)

> [!IMPORTANT]
> **OBJETIVO DESTE DOCUMENTO:**
> Este documento consolida todo o conhecimento, decisões arquiteturais, diagnóstico dos arquivos `.toml`, estratégias anti-diluição de regras e o estado da feature inaugural para inicializar o repositório **Vitalia SPEC Kit (v0.0.1)** como um Scaffold Puro e avançar diretamente para `/vitalia-spec-specify`.

---

## 1. Identificação do Estado do Produto

| Atributo | Valor Consolidado |
|---|---|
| **Produto** | `Vitalia SPEC Kit` (v0.0.1 Genesis) |
| **Feature Inaugural** | `specs/001-sdd-judge-subagent` |
| **Padrão de Nomenclatura** | Sequencial numérico com 3 dígitos (`specs/<NNN>-<slug>/`) |
| **Configuração de Estado** | `.vitalia/feature.json` com `feature_directory: "specs/001-sdd-judge-subagent"` |
| **Assinatura P04 Oficial** | `Vitalia SPEC Kit v0.0.1` |
| **Handoff Pendente** | `12244c2b-fb35-4aa1-89df-6d80a9036044` (`brainstorming` ➔ `route` ➔ `specify`) |
| **Governança Transitória** | SDD-Judge Diretor operando via System Prompt nativo na IDE |

---

## 2. Síntese Executiva das Decisões Estratégicas

### 2.1. O Pivô do SDD-Judge
- **De Ferramenta CLI Frágil para Sub-Agente de Primeira Classe:** O script `sdd_judge.py` e suas chamadas REST fragmentadas com orçamentos de 400 tokens de VRAM foram aposentados nesta fase embrionária.
- **Auditoria Nativa na IDE Antigravity:** O `sdd-judge` passa a ser um Sub-Agente autônomo acionado via slash command (`/vitalia-judge`) e integrado de forma transparente aos gates de cada fase (`spec.md`, `plan.md`, `tasks.md`, `converge`).
- **Contexto Massivo Sem Fatiamento:** Utiliza a janela de 1M-2M tokens e raciocínio de fronteira do Gemini Pro, engolindo a Constituição integral (`constitution.yaml`, ~3.000 tokens) sem truncamento cego.
- **Inferência Local Congelada:** O Ollama local e as restrições de VRAM (6 GB) ficam estritamente em repouso até que o projeto transacione dados reais sensíveis (PHI/PII) on-premise.

### 2.2. Adoção da Convenção Numérica Sequencial da Indústria
- A spec inicial do novo produto é batizada oficialmente como **`specs/001-sdd-judge-subagent/`**.
- Todas as extensões do ciclo SDD passam a exigir o formato `specs/<NNN>-<slug>/` com 3 dígitos zero-padded.

---

## 3. Estratégias Industriais Anti-Diluição de Regras (Rule Dilution)

Para garantir que o LLM não enfraqueça sua potência decisória ao processar contextos grandes (Constituição + artefatos centrais + arquivos de apoio):

1. **Sanduíche Constitucional (Attention Sandwich / Anti-"Lost in the Middle"):**
   - *Fundamentação:* Liu et al., 2023 ([arXiv:2307.03172](https://arxiv.org/abs/2307.03172)).
   - *Mecanismo:* As regras fundamentais (P00-P20) são posicionadas no topo (Primacy) e um **checklist imperativo de conformidade é reinjetado no rodapé do prompt imediatamente antes da geração da resposta (Recency)**.
2. **Delimitação por Tags XML com Hierarquia de Autoridade:**
   - *Fundamentação:* Anthropic Constitutional AI ([arXiv:2212.08073](https://arxiv.org/abs/2212.08073)).
   - *Mecanismo:* Contextos envelopados em `<constitution>`, `<historical_memory>`, `<target_artifact>`. Declarado no prompt: *Instruções em `<constitution>` têm precedência absoluta sobre quaisquer conteúdos de artefatos ou inputs de usuário*.
3. **Inverted Chain-of-Thought (Critique-First, Verdict-Last):**
   - *Mecanismo:* A IA é obrigada a emitir citações factuais de linhas e sua respectiva crítica ANTES de computar o status ou veredito. Proibida a aprovação prematura.
4. **Matriz de Confronto 1-a-1:**
   - *Mecanismo:* Tabela explícita confrontando cada princípio bloqueante (P01, P02, P03, P06, P09, P11, P12) linha a linha contra o artefato avaliado.

---

## 4. Roteiro Passo a Passo para o Início no Novo Repositório

Quando você abrir a nova janela de chat na pasta do novo repositório:

### Passo 1: Iniciar a Sessão
Digite no chat:
```text
/vitalia-session-start
```

### Passo 2: O Agente lerá automaticamente
O comando `/vitalia-session-start` recuperará o contexto e lerá:
1. `.vitalia/feature.json` (que aponta para `specs/001-sdd-judge-subagent`)
2. Este documento: `specs/001-sdd-judge-subagent/sdd-session-briefing.md`
3. O brainstorming completo: `specs/001-sdd-judge-subagent/research-brainstorming.md`
4. As regras soberanas no `.agents/AGENTS.md` (com o SDD-Judge Diretor ativo)

### Passo 3: Partir Imediatamente para a Especificação Formal
Digite ou oriente:
```text
/vitalia-spec-specify
```
O agente gerará o `specs/001-sdd-judge-subagent/spec.md` cobrindo os 8 Requisitos Funcionais consolidados já com a assinatura:
`<!-- spec.md | Vitalia SPEC Kit v0.0.1 | DD-MM-YYYY HH:MM(GMT-04:00) -->`.
