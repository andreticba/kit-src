<!-- quickstart.md | Vitalia SDD v0.6.0 | 16-10-2026 16:30(GMT-04:00) -->

# Quickstart: Validação do Workflow de Verificação Constitucional & Bootstrap

Este guia orienta a validação executável passo a passo da funcionalidade `task-verifier-workflow` e do instalador `kit-bootstrap.sh`.

---

## Pré-requisitos
- Ambiente Linux/macOS com Python 3.10+
- Repositório `kit_src` clonado
- Virtualenv local `./.venv` ativo

---

## Cenário 1: Bootstrap Seguro com Salvaguardas em Projeto Existente

### Passo 1: Simular projeto alvo com `.env` e `requirements.txt`
```bash
mkdir -p /tmp/projeto-teste && cd /tmp/projeto-teste
echo "DATABASE_URL=postgres://localhost:5432/db" > .env
echo "django==4.2.0" > requirements.txt
```

### Passo 2: Executar o bootstrap universal
```bash
/home/andre/projetos/assistidos/kit_src/kit-bootstrap.sh
```

### Validação Esperada:
- O terminal exibe mensagens destacando o início da instalação.
- Backups preventivos `.env.bak` e `requirements.txt.bak` são criados em `/tmp/projeto-teste/`.
- O arquivo `.env` preserva a linha `DATABASE_URL` intacta e adiciona as variáveis do Kit.
- O `.venv` é criado exclusivamente em `/tmp/projeto-teste/.venv/`.

---

## Cenário 2: Auditoria Adversarial de Tarefas via `/vitalia-task-verifier`

### Passo 1: Decompor tarefas com `/vitalia-spec-tasks`
```text
Executar /vitalia-spec-tasks para gerar specs/minha-feature/tasks.md
```
*Resultado*: O comando conclui sem erro de hook após a remoção de `[hooks].after`, e exibe orientação para acionar `/vitalia-task-verifier`.

### Passo 2: Executar `/vitalia-task-verifier`
```text
Acionar /vitalia-task-verifier no chat da IDE
```
*Resultado*:
1. O Context Lifting compila `~/.vitalia/tmp/task-verifier_*.json` com as regras ativas.
2. O Sub-Agente Red Team gera `specs/minha-feature/Relatório de inspeção.md`.
3. O agente apresenta o resumo no chat e **PAUSA**, solicitando confirmação.
4. O arquivo `tasks.md` permanece intacto sem carimbo.

### Passo 3: Confirmação no Chat e Aplicação do Carimbo
```text
Usuário responde no chat: "Aprovado, pode carimbar"
```
*Resultado*:
1. É gerado o backup `specs/minha-feature/tasks.md.bak`.
2. As tarefas em `tasks.md` recebem o carimbo constitucional:
   `<!-- constitutional-status: APPROVED | auditor: red-team-vitalia | ... -->`.
3. O comando `/vitalia-spec-implement` é destravado com sucesso.
