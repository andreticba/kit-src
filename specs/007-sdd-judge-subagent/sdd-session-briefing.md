<!-- sdd-session-briefing.md | Vitalia SDD v0.6.0 | 02-11-2026 18:57(GMT-04:00) -->
> **sdd-session-briefing.md | Vitalia SDD v0.6.0 | 02-11-2026 18:57(GMT-04:00)**

# Documento de Transição e Briefing Operacional: Feature 007-sdd-judge-subagent

> [!IMPORTANT]
> **OBJETIVO DESTE DOCUMENTO:**
> Este documento consolida todo o conhecimento, decisões arquiteturais, diagnóstico dos arquivos `.toml`, estratégias anti-diluição de regras e o estado da feature para permitir a abertura de uma **nova janela de chat limpa** com execução imediata de `/vitalia-session-start` e avanço direto para `/vitalia-spec-specify`.

---

## 1. Identificação do Estado Atual

| Atributo | Valor Consolidado |
|---|---|
| **Feature Ativa** | `specs/007-sdd-judge-subagent` |
| **Padrão de Nomenclatura** | Sequencial numérico com 3 dígitos (`007-sdd-judge-subagent`), alinhado ao `github/spec-kit` e RFCs |
| **Configuração Ativa** | `.vitalia/feature.json` configurado com `feature_directory: "specs/007-sdd-judge-subagent"` |
| **Handoff Pendente** | `12244c2b-fb35-4aa1-89df-6d80a9036044` (`brainstorming` ➔ `route` ➔ `specify`) |
| **Artefato de Brainstorming** | `specs/007-sdd-judge-subagent/research-brainstorming.md` (Completo e atualizado) |
| **Ambiente de Testes** | 35 testes passando (`pytest tests/`) |

---

## 2. Síntese Executiva das Decisões Estratégicas

### 2.1. O Pivô do SDD-Judge
- **De Ferramenta CLI Frágil para Sub-Agente de Primeira Classe:** O script `sdd_judge.py` e suas chamadas REST fragmentadas com orçamentos de 400 tokens de VRAM foram aposentados nesta fase embrionária.
- **Auditoria Nativa na IDE Antigravity:** O `sdd-judge` passa a ser um Sub-Agente autônomo acionado via slash command (`/vitalia-judge`) e integrado de forma transparente aos gates de cada fase (`spec.md`, `plan.md`, `tasks.md`, `converge`).
- **Contexto Massivo Sem Fatiamento:** Utiliza a janela de 1M-2M tokens e raciocínio de fronteira do Gemini Pro, engolindo a Constituição integral (`constitution.yaml`, ~3.000 tokens) sem truncamento cego.
- **Inferência Local Congelada:** O Ollama local e as restrições de VRAM (6 GB) ficam estritamente em repouso até que o projeto transacione dados reais sensíveis (PHI/PII) on-premise.

### 2.2. Adoção da Convenção Numérica Sequencial da Indústria
- O diretório da feature foi formalmente migrado de `specs/sdd-judge-subagent` para **`specs/007-sdd-judge-subagent/`**.
- Todas as extensões do ciclo SDD passam a exigir o formato `specs/<NNN>-<slug>/` com 3 dígitos zero-padded.

---

## 3. Diagnóstico Crítico dos Arquivos `.toml` do Kit

A análise do código dos arquivos `.toml` em `source/extensions/` revelou falhas arquiteturais que serão corrigidas nesta feature:

| Arquivo TOML | Problema Diagnosticado no Código Atual | Correção a Implementar |
|---|---|---|
| **`spec-specify.toml`** | Nomenclatura numérica não imposta rigidamente; hook `after` chamava script CLI legado `sdd_judge.py --mode specify`; perfil `gp_spec-specify` podava regras da constituição. | Exigir prefixo `NNN-`; substituir hook `after` pelo gate do Sub-Agente `/vitalia-judge`; descontinuar `gp_spec-specify`. |
| **`spec-plan.toml`** | **Paradoxo Temporal no Passo 3:** instruía a rodar validação CLI no `plan.md` antes mesmo do arquivo ser gerado no Passo 5; hook `after` chamava CLI legado. | Mover a validação para o Passo 6 (pós-geração); acionar o gate `/vitalia-judge --mode=plan`. |
| **`spec-tasks.toml`** | Não integrava artefatos de apoio no contexto de verificação; ausência de gate adversarial nativo de tarefas (sobreposição confusa com `task-verifier`). | Integrar leitura sob demanda de artefatos de apoio; encaminhar tarefas para o gate do Sub-Agente. |
| **`spec-implement.toml`** | Hook `after` apontava para `--mode after_task` quebrado. | Remoção de chamadas CLI obsoletas; foco na execução orientada a tarefas com validação contínua. |
| **`converge.toml`** | Invocava CLI `sdd_judge.py --mode converge` sem capacidade de inspecionar o código real da IDE. | Transformar em auditoria quadridimensional executada pelo Sub-Agente inspecionando código real e git diff na IDE. |
| **Todos** | Presença de metadados legados não utilizados (`transport.preferred = "redis"`, `hardware_profile = "lightweight"`). | Limpeza de metadados obsoletos. |

---

## 4. Estratégias Industriais Anti-Diluição de Regras (Rule Dilution)

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

## 5. Roteiro Passo a Passo para a Próxima Janela de Chat

Quando você abrir a nova janela de chat, execute o seguinte procedimento:

### Passo 1: Iniciar a Sessão
Digite no chat:
```text
/vitalia-session-start
```

### Passo 2: O Agente lerá automaticamente
O comando `/vitalia-session-start` recuperará o contexto e lerá:
1. `.vitalia/feature.json` (que aponta para `specs/007-sdd-judge-subagent`)
2. Este documento: `specs/007-sdd-judge-subagent/sdd-session-briefing.md`
3. O brainstorming completo: `specs/007-sdd-judge-subagent/research-brainstorming.md`
4. O handoff pendente: `12244c2b-fb35-4aa1-89df-6d80a9036044`

### Passo 3: Partir Imediatamente para a Especificação Formal
Digite ou instrua o agente:
```text
/vitalia-spec-specify
```
O agente gerará o `specs/007-sdd-judge-subagent/spec.md` cobrindo os 8 Requisitos Funcionais consolidados:
- **FR-001:** Numeração sequencial 3 dígitos (`specs/<NNN>-<slug>/`).
- **FR-002:** Registro de `sdd-judge` em `source/profiles/agents_catalog.yaml`.
- **FR-003:** Criação da extensão `extensions/sdd-judge.toml` e skill `skills/vitalia-judge/SKILL.md`.
- **FR-004:** Implementação das 4 técnicas anti-diluição (Sanduíche, XML, Inverted CoT, Matriz 1-a-1).
- **FR-005:** Auditoria de Fase 1 confrontando Constituição, ADRs, Learnings e ISO 29148.
- **FR-006:** Ingestão on-demand de artefatos de apoio (`requirements.md`, `research.md`, `data-model.md`, etc.).
- **FR-007:** Emissão do `Relatório de Inspeção - {fase}.md` e pausa HITL soberana.
- **FR-008:** Reconstrução e saneamento dos arquivos `.toml` do ciclo SDD (`spec-specify`, `spec-plan`, `spec-tasks`, `converge`).

---

## 6. Prompt Diretor Sugerido para o Início da Nova Sessão

Se desejar acelerar o direcionamento logo após o `/vitalia-session-start`, envie a seguinte mensagem:

```text
Estamos dando continuidade aos trabalhos da feature 007-sdd-judge-subagent. 
Leia o briefing em specs/007-sdd-judge-subagent/sdd-session-briefing.md e o handoff pendente. 
Inicie imediatamente o /vitalia-spec-specify para formalizarmos a spec.md com a reconstrução dos arquivos .toml, a padronização sequencial das specs e a criação do Sub-Agente sdd-judge aplicando as técnicas de Sanduíche Constitucional e Inverted CoT.
```
