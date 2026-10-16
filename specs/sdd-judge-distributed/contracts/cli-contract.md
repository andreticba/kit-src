<!-- cli-contract.md | Vitalia SDD v0.6.0 | 15-10-2026 20:31(GMT-04:00) -->

# Contrato de Interface CLI: sdd-judge-distributed

## 1. Visão Geral
Este documento define o contrato de linha de comando (CLI), parâmetros, saídas estruturadas e códigos de retorno para os módulos do sistema `sdd-judge-distributed`.

---

## 2. Declarações Constitucionais
- **P02 (Impacto Direto ao Desenvolvedor):** O design de saída da CLI fornece relatórios em tempo real de status por tarefa sem poluir o terminal ou exigir flags obscuras. O modo HITL apresenta dossiês claros e acionáveis para resolução com uma única tecla.
- **P07 / P09 (Privacidade e Domínio Clínico):** Não aplicável. As ferramentas de CLI operam estritamente sobre arquivos técnicos de especificação e strings de prompt de desenvolvimento.
- **P11 (Agnosticismo de Infraestrutura):** Configuração 100% orientada a variáveis de ambiente (`REDIS_URL`, `OLLAMA_HOST`, `VITALIA_AUDITOR_MODEL`, etc.), com fallbacks inteligentes para ambiente de desenvolvimento local.

---

## 3. Comandos Principais

### 3.1 Orquestrador Principal (`distributed_orchestrator`)

Responsável por fazer o parse de `tasks.md`, gerar os envelopes anti-alucinação, carregar os Redis Hashes, inicializar os Consumer Groups e coordenar a barreira de sincronização até o flush atômico.

```bash
python3 -m src.judge.distributed_orchestrator \
    --feature <feature_slug> \
    [--tasks-path <caminho_customizado>] \
    [--max-cycles <5>] \
    [--timeout-seconds <120>] \
    [--dry-run] \
    [--json-output]
```

#### Parâmetros:
- `--feature` (Obrigatório): Slug da feature (ex: `sdd-judge-distributed`).
- `--tasks-path` (Opcional): Caminho alternativo para o `tasks.md`. Default: `specs/{feature}/tasks.md`.
- `--max-cycles` (Opcional): Número máximo de loops juiz-contestador antes de disparar HITL. Default: `5`.
- `--timeout-seconds` (Opcional): Limite de tempo total da execução. Default: `180`.
- `--dry-run` (Opcional): Executa a validação e o fluxo em Redis sem regravar o arquivo em disco.
- `--json-output` (Opcional): Emite o progresso e o resultado final em JSON para integração com IDEs.

#### Exemplo de Saída no Terminal:
```text
[Vitalia SDD] Ingestão de tarefas para feature: sdd-judge-distributed
[Tasks] 18 tarefas detectadas em 4 fases.
[Redis] Ingestão em 'sdd:task:sdd-judge-distributed:*' concluída (18 hashes).
[Stream] Eventos publicados em 'sdd:events:sdd-judge-distributed'.
[Workers] Aguardando adjudicação concorrente...
--------------------------------------------------------------------------------
[T001] [Phase 1] APROVADA (Ciclo 1 | 1.8s)
[T002] [Phase 1] APROVADA (Ciclo 1 | 1.9s)
[T003] [Phase 2] REPROVADA (P05) -> Contestação aceita -> APROVADA (Ciclo 2 | 3.4s)
[T004] [Phase 2] APROVADA (Ciclo 1 | 2.1s)
...
--------------------------------------------------------------------------------
[Barreira] 18/18 tarefas APROVADAS (100%).
[Disco] Backup gerado em specs/sdd-judge-distributed/tasks.md.bak
[Disco] Escrita atômica em specs/sdd-judge-distributed/tasks.md realizada com sucesso.
[Shard] Histórico arquivado em .vitalia/sessions/shards/sdd-judge-sdd-judge-distributed-20261015.json
Status Final: SUCESSO (0 tarefas escaladas)
```

---

### 3.2 Workers Especializados (`workers`)

Executados como daemons leves ou tarefas em background pelo Orquestrador.

```bash
# 1. Worker do Juiz (Avaliação Constitucional)
python3 -m src.judge.workers.judge_worker \
    --feature <feature_slug> \
    --consumer-name <juiz-1> \
    [--model <modelo_ou_env>]

# 2. Worker do Contestador (Análise Contextual de Defesa)
python3 -m src.judge.workers.contest_worker \
    --feature <feature_slug> \
    --consumer-name <contesta-1> \
    [--model <modelo_ou_env>]

# 3. Worker do Refaturador (Reescrita Atômica de Tarefas)
python3 -m src.judge.workers.refactor_worker \
    --feature <feature_slug> \
    --consumer-name <refatura-1> \
    [--model <modelo_ou_env>]
```

---

### 3.3 Resolutor Interativo de Escalação Humana (`hitl_resolver`)

Acionado pelo Orquestrador ou invocado pelo desenvolvedor quando uma tarefa excede o limite de ciclos sem consenso.

```bash
python3 -m src.judge.hitl_resolver --feature <feature_slug> [--task-id <task_id>]
```

#### Interface do Terminal (Prompt Interativo):
```text
================================================================================
              VITALIA SDD — DOSSIÊ DE ESCALAÇÃO HITL (P17)
================================================================================
Feature: sdd-judge-distributed | Tarefa: T005 [P] [US2]
Ciclos Percorridos: 5 (Limite atingido)
Regra em Disputa: P05 (Test-First)

--- Linha Original da Tarefa ---
- [ ] T005 [P] [US2] Implementar listener de stream em src/services/consumer.py

--- Veredito do Juiz (Último Ciclo) ---
"REPROVADA: A tarefa T005 introduz lógica produtiva de rede sem teste prévio imediato."

--- Defesa do Contestador ---
"CONTESTAÇÃO: O teste unitário tests/test_consumer.py foi explicitado em T004."

--- Proposta do Refaturador ---
"- [ ] T005 [P] [US2] Implementar listener de stream em src/services/consumer.py satisfazendo testes de tests/test_consumer.py"

--------------------------------------------------------------------------------
Escolha uma ação de desempate:
  [1] Aprovar com a redação proposta pelo Refaturador
  [2] Aprovar com a redação original (Override Constitucional)
  [3] Editar a linha da tarefa manualmente agora
  [4] Fornecer instrução textual ao Refaturador e rodar novo ciclo
  [5] Abortar o pipeline e manter tasks.md original
Sua escolha [1-5]: 
```

---

## 4. Códigos de Saída (Exit Codes)

| Código | Significado | Condição | Ação do Pipeline |
| :---: | :--- | :--- | :--- |
| `0` | **Sucesso** | 100% das tarefas aprovadas; arquivo gravado atomicamente em disco. | Prossegue para a próxima fase do SDD (`/vitalia-spec-implement`). |
| `1` | **Violação Incorrigível** | Erro de sintaxe irreparável no arquivo `tasks.md` de entrada. | Bloqueia pipeline e instrui usuário a rever formato. |
| `2` | **Pausa para HITL** | Tarefas escaladas pendentes de decisão do usuário. | Interrompe o processo e exibe comando do `hitl_resolver`. |
| `3` | **Erro de Infraestrutura** | Falha de conexão com Redis ou provedor de LLM/Ollama inalcançável. | Exibe diagnóstico de rede/serviço e encerra com segurança sem alterar disco. |
| `124` | **Timeout** | Tempo de execução excedeu o `--timeout-seconds`. | Preserva chaves no Redis e permite retoma posterior. |
