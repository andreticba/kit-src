<!-- data-model.md | Vitalia SDD v0.6.0 | 16-10-2026 16:30(GMT-04:00) -->

# Modelo de Dados: Workflow de Verificação Constitucional & Universal Bootstrap

## 1. Visão Geral
Este documento especifica os modelos de dados, esquemas de artefatos e contratos de estado utilizados pelo workflow `/vitalia-task-verifier` e pelo script `kit-bootstrap.sh`. 

Ao contrário da abordagem assíncrona anterior baseada em bancos de dados voláteis (Redis Hashes e Streams), o `task-verifier-workflow` adota persistência idempotente e determinística baseada no sistema de arquivos do repositório, garantindo que o ciclo de auditoria produza artefatos imutáveis e auditáveis (`Relatório de inspeção.md`, `tasks.md.bak` e carimbos constitucionais rastreáveis).

---

## 2. Declarações Constitucionais
- **P02 (Impacto Direto ao Usuário):** A retenção preventiva do backup `tasks.md.bak` e o relatório estruturado garantem que o desenvolvedor tenha total previsibilidade sobre alterações de escopo, sem perda de histórico e com rollback instantâneo de 1 clique.
- **P06 (Proteção de Segredos):** O modelo do instalador protege chaves pré-existentes em `.env` e nunca persiste credenciais nos artefatos de auditoria.
- **P07 / P09 (Privacidade e Domínio Clínico):** Todo o processamento de dados de tarefas ocorre localmente. O relatório de inspeção manipula exclusivamente metadados de engenharia de software (identificadores de tarefas, arquivos alvo e critérios de aceite). Regras clínicas (P09) são ativadas sob demanda via Guardian Context Lifting quando o preset indicar domínio de saúde.
- **P11 (Agnosticismo Tecnológico):** Estruturas baseadas em Markdown e JSON padrão (RFC 8259), universais e interpretáveis em qualquer sistema operacional sem dependência de serviços externos.
- **P17 (Supervisão Humana / HITL):** O modelo de dados requer a confirmação textual explícita do operador no chat como campo transacional mandatório antes da gravação do status de aprovação.

---

## 3. Estruturas de Dados do Workflow

### 3.1 Dossiê Físico: `specs/{feature}/Relatório de inspeção.md`
Artefato Markdown persistido no diretório da feature ativa contendo o resultado da auditoria adversarial.

#### Seções Obrigatórias:
1. **Cabeçalho Canônico:** Metadados da auditoria (Timestamp GMT-04:00, feature, agente auditor e versão do Kit).
2. **Resumo Executivo:** Quantidade total de tarefas avaliadas, aprovadas, sob alerta e rejeitadas.
3. **Matriz de Conformidade por Tarefa:** Tabela estruturada com as seguintes colunas:
   - `ID`: Identificador da tarefa (ex: `T001`).
   - `Fase`: Fase de implementação (ex: `Setup`, `Foundational`, `US1`).
   - `User Story`: Tag de rastreabilidade (ex: `US1` ou `Transversal`).
   - `Princípios Avaliados`: Lista dos princípios aplicáveis (ex: `P01`, `P05`, `P06`, `P07`).
   - `Status`: `CONFORME`, `ALERTA` ou `VIOLAÇÃO`.
   - `Observações`: Diagnóstico conciso do parecer.
4. **Diagnóstico Detalhado de Inconformidades:** Justificativa técnica das falhas detectadas com citação da regra constitucional violada.
5. **Proposta de Refatoração:** Diffs ou blocos de substituição sugeridos para as tarefas que exigem adequação.
6. **Recomendação Final e Ação HITL:** Parecer indicando se o lote está apto para aprovação pelo desenvolvedor no chat.

---

### 3.2 Carimbo Constitucional em `tasks.md`
Metadados embutidos em comentário HTML no topo do arquivo `tasks.md` após confirmação explícita no chat.

#### Formato Canônico:
```html
<!-- constitutional-status: APPROVED | auditor: red-team-vitalia | timestamp: 2026-10-16T16:30:00-04:00 | report: Relatório de inspeção.md -->
```

#### Atributos do Carimbo:
- `constitutional-status`: `APPROVED` (único valor que autoriza `/vitalia-spec-implement`).
- `auditor`: Identificação da persona auditora (`red-team-vitalia`).
- `timestamp`: Carimbo de data/hora ISO-8601 com fuso `-04:00`.
- `report`: Caminho relativo ao artefato de auditoria que fundamentou a aprovação.

---

### 3.3 Backup Preventivo: `specs/{feature}/tasks.md.bak`
Cópia binária idêntica do arquivo `tasks.md` criada imediatamente antes da aplicação de qualquer refatoração de tarefas ou gravação do carimbo constitucional. Garante recuperação instantânea em caso de divergência ou rejeição humana pós-fato.

---

### 3.4 Context Lifting Stub: `~/.vitalia/tmp/task-verifier_<timestamp>_<hash>.json`
Estrutura JSON gerada pelo `hook_runner.py` via `guardian_context.py` contendo o payload dinâmico para o Sub-Agente Red Team.

```json
{
  "schema_version": "0.6.0",
  "workflow": "task-verifier",
  "timestamp": "16-10-2026 16:30:00(GMT-04:00)",
  "prompt": "<Missão, regras de inspeção e comando de pausa para confirmação no chat>",
  "guardian_json": {
    "sources": {
      "constitution": {
        "principles": {
          "P01": { "name": "SDD Pipeline Inviolability", "rule": "...", "severity": "BLOCKING" },
          "P05": { "name": "Test-First Architecture", "rule": "...", "severity": "BLOCKING" },
          "P06": { "name": "Secrets Never in Git", "rule": "...", "severity": "BLOCKING" },
          "P07": { "name": "Privacy & Confidentiality", "rule": "...", "severity": "BLOCKING" },
          "P17": { "name": "EU AI Act & Human Oversight", "rule": "...", "severity": "BLOCKING" }
        }
      },
      "active_feature": {
        "feature_directory": "specs/task-verifier-workflow",
        "spec_file": "specs/task-verifier-workflow/spec.md",
        "tasks_file": "specs/task-verifier-workflow/tasks.md"
      }
    }
  }
}
```

---

## 4. Ciclo de Vida e Máquina de Estados (FSM) da Verificação

```
[ GERADO ] (via /vitalia-spec-tasks)
    │
    ▼
[ EM_AUDITORIA ] (acionamento de /vitalia-task-verifier)
    │
    ├── Gera: specs/{feature}/Relatório de inspeção.md
    │
    ▼
[ AGUARDANDO_HITL ] (pausa obrigatória; agente apresenta relatório no chat)
    │
    ├── Se REJEITADO no Chat ────► [ REFATORANDO_MANUAL ]
    │
    └── Se APROVADO no Chat
            │
            ├── Cria: specs/{feature}/tasks.md.bak
            ├── Aplica refatorações acordadas
            ├── Grava: Carimbo <!-- constitutional-status: APPROVED -->
            │
            ▼
        [ APROVADO_CONSTITUCIONALMENTE ]
            │
            ▼
    [ LIBERADO_IMPLEMENT ] (/vitalia-spec-implement destravado)
```
