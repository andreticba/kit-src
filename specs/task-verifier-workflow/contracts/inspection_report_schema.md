<!-- inspection_report_schema.md | Vitalia SDD v0.6.0 | 16-10-2026 16:30(GMT-04:00) -->

# Contrato de Interface: Relatório de Inspeção Constitucional de Tarefas

## 1. Identificação
* **Nome do Artefato:** `specs/{feature}/Relatório de inspeção.md`
* **Tipo:** Documento Markdown Estruturado (Relatório de Auditoria Adversarial)
* **Emissor:** Sub-Agente Red Team Constitucional (`/vitalia-task-verifier`)
* **Consumidor:** Desenvolvedor (HITL) e Gatekeeper de Implementação (`/vitalia-spec-implement`)

---

## 2. Estrutura Obrigatória do Documento

### 2.1 Cabeçalho
```markdown
<!-- Relatório de inspeção.md | Vitalia SDD v0.6.0 | DD-MM-YYYY HH:MM(GMT-04:00) -->
# Relatório de Inspeção Constitucional: [FEATURE_NAME]

**Data da Auditoria:** DD-MM-YYYY HH:MM(GMT-04:00)  
**Auditor:** Red Team Constitucional (Vitalia SDD)  
**Feature Alvo:** `specs/[FEATURE_NAME]`  
**Status Preliminar:** [APROVAÇÃO RECOMENDADA | AJUSTES NECESSÁRIOS | BLOQUEIO CONSTITUCIONAL]  
```

### 2.2 Resumo Estatístico de Cobertura
```markdown
## 1. Resumo Executivo
* **Total de Tarefas Auditadas:** [N]
* **Tarefas Conformes:** [N] ([%])
* **Tarefas com Alertas / Ajustes Sugeridos:** [N]
* **Tarefas com Violações Críticas:** [N]
```

### 2.3 Matriz de Conformidade
Tabela Markdown contendo 1 linha para cada tarefa do `tasks.md`:
```markdown
## 2. Matriz de Conformidade Constitucional

| ID | Fase | User Story | Princípios Testados | Parecer | Diagnóstico |
|---|---|---|---|:---:|---|
| T001 | Setup | Transversal | P01, P04, P11 | CONFORME | Tarefa de setup atômica e agnóstica |
| T002 | Foundational | US1 | P01, P05, P07 | ALERTA | Falta explicitar mock de dados de teste |
```

Valores permitidos para a coluna `Parecer`:
- `CONFORME`: Atende a todos os princípios aplicáveis.
- `ALERTA`: Não-bloqueante, mas com recomendação de melhoria de clareza ou escopo.
- `VIOLAÇÃO`: Bloqueante (ex: credenciais em código P06, ausência de testes P05, bypass de pipeline P01).

### 2.4 Proposta de Refatoração Sintética
Para cada tarefa classificada como `ALERTA` ou `VIOLAÇÃO`:
```markdown
## 3. Refatorações Recomendadas

### Tarefa [Txxx]
* **Redação Original:**
  `- [ ] Txxx ...`
* **Violação Identificada:**
  `[Princípio Pxx]: Explicação detalhada da inconformidade.`
* **Redação Proposta (Corrigida):**
  `- [ ] Txxx ...`
```

### 2.5 Conclusão e Gatilho HITL
```markdown
## 4. Parecer Conclusivo & Handoff Humano

> [!IMPORTANT]
> **Aprovação Soberana do Desenvolvedor (HITL Gate):**
> Nenhuma alteração foi realizada no arquivo `tasks.md`.
> Para aplicar as refatorações sugeridas e receber o carimbo constitucional que destrava o `/vitalia-spec-implement`, responda no chat confirmando a aprovação (ex: *"Aprovado, pode carimbar"*).
```
