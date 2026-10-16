<!-- architecture-diagrams.md | Vitalia SDD v0.6.0 | 16-10-2026 14:49(GMT-04:00) -->
# Diagramas de Arquitetura: Task Verifier Workflow & Bootstrap Universal

**Data:** 16-10-2026 14:49(GMT-04:00)  
**Feature:** `task-verifier-workflow`  
**Documentos Relacionados:**
- [research-brainstorming.md](file:///home/andre/projetos/assistidos/kit_src/specs/task-verifier-workflow/research-brainstorming.md)
- [research.md](file:///home/andre/projetos/assistidos/kit_src/specs/task-verifier-workflow/research.md)
- [kit_judge_audit.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-distributed/kit_judge_audit.md)

---

## 1. Segregação de Camadas: Execução Nativa na IDE vs. Isolamento Local

Este diagrama demonstra a eliminação de chamadas REST para APIs externas avulsas e o isolamento de dados dentro da sessão autorizada da IDE, protegendo a cota de tokens e garantindo zero vazamento de PII/PHI.

```mermaid
flowchart TD
    subgraph CAMADA_IDE ["1. Camada Interativa & Orquestração (Nativa no Antigravity IDE)"]
        direction TB
        DEV["👤 Desenvolvedor"] <--> AGY["⚡ Antigravity IDE (Contexto Holístico de Fronteira)"]
        
        subgraph TIME_AGENTES ["Agentes Especializados do Pipeline SDD"]
            GENERATOR["📝 Agente Construtor (/vitalia-spec-tasks)"]
            VERIFIER["🛡️ Promotor Constitucional (/vitalia-task-verifier - Red Team)"]
            IMPLEMENTOR["💻 Agente Implementador (/vitalia-spec-implement)"]
        end

        AGY <--> TIME_AGENTES
    end

    subgraph ARTEFATOS_SDD ["2. Artefatos Físicos do Workspace Local"]
        SPEC["📋 specs/{feature}/spec.md"]
        PLAN["🗺️ specs/{feature}/plan.md"]
        TASKS["✅ specs/{feature}/tasks.md"]
        BAK["💾 tasks.md.bak (Backup Preventivo)"]
    end

    subgraph ISOLAMENTO_PRIVACIDADE ["3. Perímetro de Segurança & Privacidade (Zero-Leak)"]
        direction TB
        LOCAL_ENV["🔒 Sessão Local do Desenvolvedor"]
        NO_CLOUD["🚫 Zero Chamadas REST a APIs de Terceiros"]
        NO_LEAK["🛡️ PII / PHI Protegidos (P07 & P09)"]
        LOCAL_ENV --- NO_CLOUD
        NO_CLOUD --- NO_LEAK
    end

    TIME_AGENTES -->|"Gera rascunho preliminar"| TASKS
    TASKS -->|"Lido para auditoria holística"| VERIFIER
    VERIFIER -->|"Ajustes & Veredito Final"| TASKS
    TASKS -.->|"Cópia de segurança prévia"| BAK
    CAMADA_IDE --- ISOLAMENTO_PRIVACIDADE
```

---

## 2. Injeção Dinâmica de Regras Constitucionais via Context Lifting (§11)

Este diagrama detalha como o `task-verifier.toml` permanece 100% agnóstico e sem regras fixas no prompt, recebendo os princípios (P00-P17) dinamicamente podados pelo Guardião para a feature ativa.

```mermaid
sequenceDiagram
    autonumber
    actor Dev as "👤 Desenvolvedor"
    participant IDE as "⚡ Antigravity IDE"
    participant HookRunner as "⚙️ hook_runner.py"
    participant Guardian as "🛡️ guardian_context.py (§11)"
    participant TmpDisk as "📁 ~/.vitalia/tmp/"
    participant SkillPrompt as "📜 task-verifier (Prompt)"

    Dev->>IDE: Aciona /vitalia-task-verifier
    IDE->>HookRunner: Executa hook antes do workflow
    HookRunner->>Guardian: Invoca compilador de contexto com yaml_sources=["constitution"]
    Note over Guardian: Lê profiles/ e .vitalia/feature.json<br/>Poda os princípios aplicáveis ao domínio ativo
    Guardian->>TmpDisk: Grava arquivo gordo: task-verifier_<timestamp>.json
    HookRunner-->>IDE: Emite Stub JSON apontando para o arquivo temporário
    IDE->>TmpDisk: Lê o arquivo temporário via view_file
    TmpDisk-->>SkillPrompt: Carrega prompt (missão) + guardian_json (regras dinâmicas)
    Note over SkillPrompt: Audita tasks.md aplicando P09/P07 (se saúde),<br/>P11/P04 (se infra) ou P02/P05 (se UI)
```

---

## 3. Fluxo Ponta a Ponta: Da Concepção à Implementação

Este diagrama mostra o ciclo de vida SDD refinado, com o handoff explícito de `spec-tasks` para `task-verifier` antes de permitir qualquer escrita de código produtivo.

```mermaid
flowchart LR
    subgraph ETAPA1 ["Fase 1: Especificação"]
        SPEC_SPECIFY["/vitalia-spec-specify"] --> SPEC_PLAN["/vitalia-spec-plan"]
    end

    subgraph ETAPA2 ["Fase 2: Decomposição de Tarefas"]
        SPEC_PLAN --> SPEC_TASKS["/vitalia-spec-tasks<br/>(Gera tasks.md preliminar por US)"]
    end

    subgraph ETAPA3 ["Fase 3: Portão Constitucional Red Team"]
        SPEC_TASKS -->|"Handoff Explícito"| TASK_VERIFIER["/vitalia-task-verifier<br/>(Auditoria Dinâmica na IDE)"]
        
        TASK_VERIFIER --> REPORT["📄 specs/{feature}/Relatório de inspeção.md<br/>(Dossiê Completo de Auditoria)"]
        REPORT --> DEV_CONFIRM{"Confirmação Explícita no Chat pelo Desenvolvedor?"}
        DEV_CONFIRM -->|"Não / Ajustar"| HITL["🚨 Refatoração Interativa / Override"]
        HITL --> REPORT
        DEV_CONFIRM -->|"SIM (Aprovado)"| STAMP["🏷️ Carimbo de Conformidade no tasks.md<br/>+ Backup Preventivo tasks.md.bak"]
    end

    subgraph ETAPA4 ["Fase 4: Construção com TDD"]
        STAMP --> SPEC_IMPLEMENT["/vitalia-spec-implement<br/>(Execução Rigorosa T001..Tn)"]
    end
```

---

## 4. Arquitetura Universal de Bootstrap (`kit-bootstrap.sh`)

Este diagrama ilustra o fluxo de instalação: ele anuncia e gerencia explicitamente o `.venv` local com tratamento de colisão em `requirements.txt`, sincroniza os arquivos do Kit para `~/.vitalia/` e delega a resolução dinâmica de imports para o módulo canônico `kit_env_bootstrap.py`.

```mermaid
flowchart TD
    subgraph ENTRADA ["1. Entrada do Usuário ou Repositório"]
        SCRIPT["bash kit-bootstrap.sh [caminho_opcional]"]
        DETECT{"Detectou ./source ou ./kit-global?"}
        PROMPT_USER["read -p: Pergunta caminho da pasta fonte ao usuário"]
        SCRIPT --> DETECT
        DETECT -->|Não| PROMPT_USER
        DETECT -->|Sim| SRC_DIR["Diretório Fonte Identificado"]
        PROMPT_USER --> SRC_DIR
    end

    subgraph PROJETO_LOCAL ["2. Workspace Local do Projeto (Passo 1 Explicito)"]
        BANNER["📢 Terminal: Configuração do .venv, Dependências e .env"]
        
        subgraph GESTAO_REQ ["Gestão de Dependências (requirements.txt)"]
            CHECK_REQ{"Já existe requirements.txt?"}
            LAYER_REQ["Opção A: Instalação em Camadas (requirements.txt + requirements-kit.txt)"]
            MERGE_REQ["Opção B: Fusão Segura com Backup (.bak)"]
            NEW_REQ["Cria requirements.txt com dependências do Kit"]
            VENV["./.venv/ (Virtualenv Local do Projeto)"]
        end

        subgraph GESTAO_ENV ["Gestão de Variáveis de Ambiente (.env)"]
            CHECK_ENV{"Já existe .env no projeto?"}
            APPEND_ENV["Gera .env.bak e adiciona chaves do Kit ausentes"]
            NEW_ENV["Cria .env a partir de .env.example do Kit"]
            ENV_FILE["./.env (Ambiente Provisionado)"]
        end

        SRC_DIR --> BANNER
        BANNER --> CHECK_REQ
        BANNER --> CHECK_ENV
        CHECK_REQ -->|Sim: Já existe| LAYER_REQ
        CHECK_REQ -->|Sim: Deseja merge| MERGE_REQ
        CHECK_REQ -->|Não| NEW_REQ
        LAYER_REQ --> VENV
        MERGE_REQ --> VENV
        NEW_REQ --> VENV
        CHECK_ENV -->|Sim: Já existe| APPEND_ENV
        CHECK_ENV -->|Não| NEW_ENV
        APPEND_ENV --> ENV_FILE
        NEW_ENV --> ENV_FILE
    end

    subgraph KIT_BOOTSTRAP_TOOL ["3. Resolução Nativa de Imports (kit_env_bootstrap.py)"]
        TOOL["source/src/kit_env_bootstrap.py"]
        FIND_ROOT["find_project_root(): localiza workspace"]
        INJECT_VENV["inject_venv(): injeta site-packages do .venv em sys.path"]
        INJECT_KIT["_KIT_SCRIPTS_DIR: injeta ~/.vitalia/src em sys.path"]
        TOOL --> FIND_ROOT
        FIND_ROOT --> INJECT_VENV
        INJECT_VENV --> INJECT_KIT
    end

    subgraph KIT_GLOBAL ["4. Instalação Global em ~/.vitalia/"]
        DEST_BIN["~/.vitalia/bin/"]
        DEST_EXT["~/.vitalia/extensions/"]
        DEST_PROF["~/.vitalia/profiles/"]
        DEST_SRC["~/.vitalia/src/"]
        DEST_MEM["~/.vitalia/memory/ (Preservado / Não Sobrescrito)"]
    end

    SRC_DIR -->|"rsync limpo e agnóstico"| KIT_GLOBAL
    VENV -.-> TOOL
    DEST_SRC -.-> TOOL
```
