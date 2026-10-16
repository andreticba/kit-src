<!-- quickstart.md | Vitalia SDD v0.6.0 | 15-10-2026 20:32(GMT-04:00) -->

# Guia de Início Rápido (Quickstart): sdd-judge-distributed

## 1. Visão Geral
Este guia fornece um passo a passo prático para testar e validar o ecossistema distribuído de julgamento de tarefas (`sdd-judge-distributed`) em ambiente local, cobrindo o fluxo padrão de aprovação, contestação em loop e resolução humana (HITL).

---

## 2. Declarações Constitucionais
- **P02 (Impacto Direto ao Desenvolvedor):** Fornece um roteiro de teste reprodutível de ponta a ponta em menos de 2 minutos, sem risco de corrupção do workspace de produção.
- **P07 / P09 (Privacidade e Domínio Clínico):** Não aplicável. Todos os testes utilizam dados simulados de engenharia de software em pastas isoladas de fixtures.
- **P11 (Agnosticismo de Infraestrutura):** As instruções utilizam Docker ou instâncias nativas de Redis e Ollama, validando qualquer modelo configurado via variáveis de ambiente.

---

## 3. Pré-requisitos do Sistema

Verifique se os serviços essenciais estão operacionais:

```bash
# 1. Verificar Redis (Local ou Container)
redis-cli ping
# Resposta esperada: PONG

# 2. Verificar Ollama e modelo de SLM configurado
curl -s http://localhost:11434/api/tags | grep "qwen2.5-coder:3b"
# Resposta esperada: presença da tag do modelo

# 3. Configurar variáveis de ambiente na sessão
export REDIS_URL="redis://localhost:6379/0"
export OLLAMA_HOST="http://localhost:11434"
export VITALIA_AUDITOR_MODEL="qwen2.5-coder:3b"
export VITALIA_REFACTOR_MODEL="qwen2.5-coder:3b"
```

---

## 4. Cenário de Validação Ponta a Ponta

### Passo 1: Criar Fixture de Teste
Crie um arquivo de teste isolado `tests/fixtures/sample_tasks.md` simulando 3 casos canônicos:
1. **T001:** Tarefa simples e perfeitamente aderente (Aprovação no Ciclo 1).
2. **T002:** Tarefa com ambiguidade de teste prévio P05 (Reprovada no Ciclo 1 $\rightarrow$ Contestada/Refatorada $\rightarrow$ Aprovada no Ciclo 2).
3. **T003:** Tarefa com conflito intencional estrito para disparar escalação HITL (Ciclos 1 a 5 $\rightarrow$ Escalação).

```bash
mkdir -p tests/fixtures
cat << 'EOF' > tests/fixtures/sample_tasks.md
# Tasks: Exemplo Quickstart

## Fase 1: Setup e Infraestrutura
- [ ] T001 [P] [US1] Configurar cliente Redis em src/infra/redis_client.py com testes unitários em tests/test_redis.py

## Fase 2: Implementação de Core
- [ ] T002 [P] [US2] Implementar motor de FSM em src/core/fsm.py
- [ ] T003 [P] [US2] Modificar credenciais de produção no código de src/auth/keys.py
EOF
```

---

### Passo 2: Executar o Orquestrador Distribuído
Execute o orquestrador apontando para a fixture criada:

```bash
python3 -m src.judge.distributed_orchestrator \
    --feature quickstart-demo \
    --tasks-path tests/fixtures/sample_tasks.md \
    --max-cycles 5
```

#### Comportamento Observado:
1. O orquestrador sintetiza os envelopes contextuais e carrega as chaves `sdd:task:quickstart-demo:*` no Redis.
2. `T001` é avaliada pelo Juiz e recebe veredito `APROVADA` imediatamente (~1.8s).
3. `T002` é inicialmente marcada com `REPROVADA` por falta de referência textual a testes; o Contestador apresenta a tese de contexto, o Refaturador ajusta a redação e o Juiz emite `APROVADA` no ciclo 2 (~3.5s).
4. `T003` viola a regra P06 (Segredos/Credenciais); o loop esgota as 5 tentativas e o status transita para `ESCALADA_HITL`.
5. O processo pausa emitindo código de saída `2` e exibe o comando de resolução humana.

---

### Passo 3: Resolver a Escalação Humana (HITL)
Invoque o resolvedor interativo no terminal:

```bash
python3 -m src.judge.hitl_resolver \
    --feature quickstart-demo \
    --task-id T003
```

- No menu interativo, selecione a opção `[3]` para editar a tarefa ou `[1]` para aplicar override.
- Digite uma nova redação conforme a boa prática:
  `"- [ ] T003 [P] [US2] Carregar chaves de autenticação exclusivamente a partir de variáveis de ambiente em src/auth/keys.py"`
- O status de `T003` transita para `APROVADA`.

---

### Passo 4: Conclusão e Flush em Disco
Com todas as 3 tarefas no status `APROVADA`:
1. A barreira de sincronização é satisfeita ($3/3$).
2. O arquivo `tests/fixtures/sample_tasks.md.bak` é criado como salvaguarda.
3. O arquivo `tests/fixtures/sample_tasks.md` é regravado de forma atômica contendo a redação final validada.
4. O shard de sessão é salvo em `.vitalia/sessions/shards/`.
5. A execução termina com código `0`.
