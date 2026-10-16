<!-- spec.md | Vitalia SDD v0.6.0 | 16-10-2026 16:15(GMT-04:00) -->
# Especificação de Funcionalidade: Workflow de Verificação Constitucional de Tarefas & Universal Bootstrap

**Data:** 16-10-2026 16:15(GMT-04:00)  
**Feature:** `task-verifier-workflow`  
**Status:** APPROVED (Validado pelo SDDJudge)  
**Artefatos Relacionados:**
- [research-brainstorming.md](file:///home/andre/projetos/assistidos/kit_src/specs/task-verifier-workflow/research-brainstorming.md)
- [architecture-diagrams.md](file:///home/andre/projetos/assistidos/kit_src/specs/task-verifier-workflow/architecture-diagrams.md)
- [research.md](file:///home/andre/projetos/assistidos/kit_src/specs/task-verifier-workflow/research.md)

---

## 1. Contexto e Objetivo (O Quê e Por Quê)

O Vitalia Kit (v0.6.0) adota o paradigma SDD (*Spec-Driven Development*), onde a transição entre o planejamento de engenharia (`spec-tasks`) e a execução do código (`spec-implement`) depende de um gate constitucional rigoroso. A tentativa anterior (`sdd-judge-distributed`) buscou implementar esse gate como um conjunto de daemons assíncronos em segundo plano baseados em Redis Streams e chamadas diretas a LLMs locais/remotos. Esse arranjo colapsou devido a seis falhas sistêmicas críticas:
1. Ruptura de imports (`ModuleNotFoundError: No module named 'source'`);
2. Tempestade de eventos concorrentes no Redis gerando loops e escalada HITL prematura;
3. Re-leitura cega de linhas originais em vez de sugestões refatoradas;
4. Falsos testes unitários que mockavam a FSM sem rodar o orquestrador;
5. Violação de P11 por hardcoding de modelos de IA no código;
6. Saturação de VRAM na GPU local (6GB) por múltiplos daemons concorrentes, travando a máquina do desenvolvedor.

O objetivo do `task-verifier-workflow` é **substituir completamente a abordagem de daemons externos por uma arquitetura nativa, determinística e integrada à IDE Antigravity**. 
O gate opera via comando `/vitalia-task-verifier`, utilizando um **Sub-Agente Red Team Constitucional** que roda dentro da sessão da IDE. As regras de auditoria não são estáticas nem hardcoded em TOMLs, sendo injetadas dinamicamente pelo **Guardian (§11 Context Lifting)** a partir do perfil e domínio ativos do projeto.

A aprovação das tarefas segue um protocolo estrito de **Human-in-the-Loop (HITL)**: o agente gera e apresenta obrigatoriamente o artefato `specs/{feature}/Relatório de inspeção.md`. O carimbo constitucional no `tasks.md` e o destravamento de `/vitalia-spec-implement` **NUNCA** ocorrem de forma automática ou silenciosa; eles dependem mandatoriamente da **confirmação explícita do desenvolvedor no chat**.

Complementarmente, a especificação redefine o script `kit-bootstrap.sh` para ser agnóstico, universal para publicação no GitHub, provisionando o ambiente virtual Python (`.venv`) no projeto local, orquestrando imports via o motor nativo `kit_env_bootstrap.py`, e aplicando políticas não-destrutivas de salvaguarda e backup para arquivos preexistentes `requirements.txt` e `.env`.

---

## 2. Requisitos Funcionais (FR-xxx)

### FR-001: Auditoria Adversarial Nativa na IDE com Sub-Agente Red Team
- **Descrição:** O sistema **MUST** executar o workflow `/vitalia-task-verifier` nativamente no ambiente da IDE Antigravity através de um Sub-Agente Red Team Constitucional. O auditor analisa cada tarefa em `tasks.md` confrontando-a com a `spec.md`, avaliando conformidade de requisitos, testabilidade e integridade sem realizar chamadas REST externas com chaves de API próprias nem depender de daemons em background.
- **Impacto ao Usuário (P02):** Elimina sobrecargas de VRAM da GPU local e travamentos no ambiente de desenvolvimento, fornecendo feedback interativo imediato diretamente na interface da IDE.
- **Governança e Privacidade (P07, P09, P17):** Esta funcionalidade constitui ferramenta interna de desenvolvimento de software; não manipula dados clínicos, biomarcadores ou diagnósticos (Medical Safety Gate P09 não ativado). Em aderência a P07 e P17, o auditor processa apenas metadados técnicos de tarefas e código-fonte no perímetro local da IDE, sem armazenar dados pessoais (PII/PHI).

### FR-002: Injeção Dinâmica de Regras Constitucionais via Context Lifting (§11)
- **Descrição:** O comando `task-verifier.toml` **MUST** obter seu catálogo de regras através do mecanismo de Context Lifting (§11) do Guardian. O `hook_runner.py` compila em runtime o arquivo temporário `~/.vitalia/tmp/task-verifier_<timestamp>_<hash>.json` com a constituição podada e os perfis de domínio ativos, proibindo regras de domínio estáticas no TOML.
- **Impacto ao Usuário (P02):** Adapta automaticamente o rigor da auditoria ao domínio ativo (software, clínico ou educacional) sem exigir que o desenvolvedor reconfigure manualmente parâmetros ou edite arquivos de configuração.
- **Governança e Privacidade (P07, P09, P17):** Assegura fundamentação dinâmica na constituição viva do projeto (P01, P03), garantindo que regras de segurança clínica (P09) e de privacidade (P07) sejam aplicadas proporcionalmente à classificação do projeto.

### FR-003: Geração Mandatória do Relatório de Inspeção
- **Descrição:** O Sub-Agente Red Team **MUST** analisar integralmente as tarefas de `specs/{feature}/tasks.md` e gerar obrigatoriamente o artefato físico `specs/{feature}/Relatório de inspeção.md` contendo a matriz de conformidade por tarefa, diagnóstico de desvios e propostas de refatoração para tarefas não conformes.
- **Impacto ao Usuário (P02):** Oferece visibilidade completa, estruturada e auditável sobre o estado de qualidade do planejamento, poupando o desenvolvedor de revisões manuais cegas antes do início da codificação.
- **Governança e Privacidade (P07, P09, P17):** Documenta a trilha formal de conformidade da feature para supervisão e auditoria algorítmica (Art. 14 EU AI Act / P17), sem retenção de dados confidenciais fora do repositório local.

### FR-004: Confirmação Explícita Mandatória no Chat (HITL Gate Soberano)
- **Descrição:** O sistema **MUST NOT** realizar carimbo ou aprovação automática em `tasks.md`. Após gerar e apresentar o `Relatório de inspeção.md`, o agente **MUST** suspender a execução e solicitar a confirmação explícita do desenvolvedor no chat para aprovação do plano.
- **Impacto ao Usuário (P02):** Mantém a soberania integral do desenvolvedor sobre a base de código e os planos de entrega, eliminando modificações indesejadas ou commits silenciosos em `tasks.md`.
- **Governança e Privacidade (P07, P09, P17):** Implementa o princípio de supervisão humana efetiva (*Human Oversight* - EU AI Act Art. 14 / P17), garantindo que nenhuma decisão de engenharia seja adotada sem validação humana consciente.

### FR-005: Carimbo Constitucional Atômico e Backup Preventivo
- **Descrição:** Somente após receber a confirmação explícita no chat, o sistema **MUST** criar uma cópia de segurança `specs/{feature}/tasks.md.bak`, aplicar as refatorações aprovadas e gravar o carimbo constitucional no cabeçalho do `tasks.md`, desbloqueando o comando `/vitalia-spec-implement`.
- **Impacto ao Usuário (P02):** Protege o desenvolvedor contra corrupção acidental de tarefas e oferece capacidade de reversão instantânea (rollback em 1 comando) com histórico de auditoria transparente.
- **Governança e Privacidade (P07, P09, P17):** Garante a integridade e rastreabilidade dos artefatos do pipeline SDD (P01, P04), assegurando que o implementador execute exclusivamente tarefas chanceladas e auditáveis.

### FR-006: Desacoplamento e Handoff Formal em `spec-tasks`
- **Descrição:** A extensão `spec-tasks.toml` **MUST** ter seu hook `[hooks].after` removido, eliminando chamadas síncronas que geravam loops. Ao concluir a decomposição de tarefas, o comando **MUST** orientar formalmente o desenvolvedor a acionar o workflow independente `/vitalia-task-verifier`.
- **Impacto ao Usuário (P02):** Elimina interrupções espúrias e travamentos ao final do planejamento, desacoplando o momento criativo de decomposição do momento de auditoria adversarial.
- **Governança e Privacidade (P07, P09, P17):** Garante a separação de deveres (*Separation of Duties*) no pipeline de governança de software (P01), assegurando independência entre o agente projetista e o auditor.

### FR-007: Universal Bootstrap com Gestão de `.venv` Local e Mapeamento de Imports
- **Descrição:** O script `kit-bootstrap.sh` **MUST** criar ou gerenciar o ambiente virtual Python (`.venv`) exclusivamente na raiz do projeto local (`./.venv`), sincronizar o Kit em `~/.vitalia/` e orquestrar os pontos de entrada através do motor `kit_env_bootstrap.py` para resolução dinâmica de dependências e imports em `sys.path`.
- **Impacto ao Usuário (P02):** Permite clonar o repositório em qualquer distribuição Linux/macOS e executar a instalação com 1 comando, sem quebras de `ModuleNotFoundError` ou contaminação do ambiente global.
- **Governança e Privacidade (P07, P09, P17):** Assegura agnosticismo de infraestrutura e reprodutibilidade tecnológica (P11), operando em ambiente isolado sem acesso a redes não autorizadas ou dependência de configurações proprietárias do host.

### FR-008: Salvaguardas Não-Destrutivas contra Colisão de `requirements.txt` e `.env`
- **Descrição:** O processo de bootstrap via `kit-bootstrap.sh` **MUST** detectar arquivos preexistentes `requirements.txt` e `.env`, gerando backups preventivos (`.bak`) e oferecendo instalação em camadas ou merge aditivo de chaves ausentes, sem nunca sobrescrever credenciais ou bibliotecas preexistentes.
- **Impacto ao Usuário (P02):** Protege integralmente as dependências e variáveis de ambiente configuradas no projeto do desenvolvedor, eliminando qualquer risco de perda de configurações ou credenciais locais.
- **Governança e Privacidade (P07, P09, P17):** Previne sobrescrita indevida de segredos corporativos e chaves criptográficas (P06), garantindo integridade e conformidade de segurança no ambiente de desenvolvimento local (P07).

---

## 3. Critérios de Sucesso e Não-Funcionais (SC-xxx)

- **SC-001 (Zero Chamadas Externas de API):** 100% da verificação constitucional é realizada dentro do contexto nativo da sessão da IDE, sem requisições HTTP para provedores externos de LLM ou dependência de chaves de API pagas.
- **SC-002 (Preservação de Recursos de Hardware):** Zero processos daemons em segundo plano consumindo VRAM da GPU local. O consumo de memória RAM do processo `hook_runner` não deve exceder 50MB.
- **SC-003 (Dinamismo Constitucional):** 100% das regras avaliadas são lidas diretamente do stub gerado pelo Guardian §11 (`~/.vitalia/tmp/task-verifier_*.json`), com zero regras estáticas hardcoded no `task-verifier.toml`.
- **SC-004 (Soberania HITL Estrita):** Nenhuma alteração é gravada em `tasks.md` sem a geração prévia de `specs/{feature}/Relatório de inspeção.md` E a confirmação textual explícita do desenvolvedor no chat.
- **SC-005 (Integridade e Rollback):** Em 100% das aprovações com modificação de tarefas, o arquivo de segurança `tasks.md.bak` é mantido intacto no diretório da feature.
- **SC-006 (Bootstrap Seguro e Idempotente):** O script `kit-bootstrap.sh` pode ser executado múltiplas vezes em projetos existentes sem sobrescrever ou corromper arquivos preexistentes `.env` ou `requirements.txt`.
- **SC-007 (Resolução Universal de Módulos):** Zero ocorrências de `ModuleNotFoundError` em qualquer comando do Kit após o bootstrap, validado via suite de testes automatizados executando no `.venv` do projeto.

---

## 4. Cenários de Aceitação (User Scenarios - Given / When / Then)

### Cenário 1: Auditoria com Aprovação Direta após Apresentação do Relatório
- **Given** que o desenvolvedor concluiu a decomposição de tarefas via `/vitalia-spec-tasks`,
- **And** o arquivo `specs/nova-feature/tasks.md` contém 12 tarefas aderentes a P01-P20,
- **When** o desenvolvedor executa o comando `/vitalia-task-verifier`,
- **Then** o sistema gera o contexto via Guardian Context Lifting em `~/.vitalia/tmp/task-verifier_*.json`,
- **And** o Sub-Agente Red Team analisa as 12 tarefas e gera `specs/nova-feature/Relatório de inspeção.md` com status 100% CONFORME,
- **And** o agente apresenta o resumo do relatório no chat e solicita confirmação explícita para aprovação,
- **When** o desenvolvedor responde explicitamente no chat: *"Aprovado, pode carimbar"*,
- **Then** o sistema gera `specs/nova-feature/tasks.md.bak`, grava o carimbo `constitutional-status: APPROVED` em `tasks.md` e informa que `/vitalia-spec-implement` está liberado.

### Cenário 2: Auditoria com Detecção de Violações e Ajuste Interativo
- **Given** que o arquivo `tasks.md` possui a tarefa `T004 [US2] Criar formulário de cartão de crédito e persistir CVV no banco`, violando P06 (Segredos) e P07 (Privacidade),
- **When** o desenvolvedor executa `/vitalia-task-verifier`,
- **Then** o Sub-Agente Red Team identifica a violação crítica e gera o `Relatório de inspeção.md` com status VIOLAÇÃO para T004,
- **And** propõe a refatoração segura: `T004 [US2] Integrar com tokenização PCI-DSS do gateway sem persistir CVV local`,
- **And** apresenta o relatório no chat com as diferenças destacadas, pausando para decisão humana,
- **When** o desenvolvedor concorda e responde no chat: *"Aprovo com a refatoração sugerida"*,
- **Then** o sistema gera o backup `tasks.md.bak`, atualiza a linha T004 no `tasks.md`, insere o carimbo `constitutional-status: APPROVED` e registra a aprovação.

### Cenário 3: Tentativa de Bypass sem Confirmação no Chat
- **Given** que o `Relatório de inspeção.md` foi gerado e apresentado ao desenvolvedor,
- **When** o desenvolvedor tenta executar `/vitalia-spec-implement` sem ter confirmado a aprovação no chat,
- **Then** o gate do `spec-implement` detecta a ausência do carimbo `constitutional-status: APPROVED` em `tasks.md`,
- **And** bloqueia a execução, orientando o desenvolvedor a concluir a validação em `/vitalia-task-verifier`.

### Cenário 4: Bootstrap em Projeto Legado com Dependências Preexistentes
- **Given** um projeto com `requirements.txt` existente (contendo `django==4.2` e `psycopg2`) e `.env` configurado com `DATABASE_URL`,
- **When** o desenvolvedor executa `./kit-bootstrap.sh`,
- **Then** o script detecta os arquivos preexistentes,
- **And** notifica o desenvolvedor no terminal, gerando os backups `requirements.txt.bak` e `.env.bak`,
- **And** instala as dependências do Kit sem remover as do projeto original,
- **And** adiciona ao `.env` apenas os parâmetros essenciais do Kit (`VITALIA_ENVIRONMENT=development`), mantendo o `DATABASE_URL` intacto.

---

## 5. Limites e Não-Escopo (Out of Scope)

1. **Inferência de LLM via Processos Externos:** Não faz parte do escopo deste workflow criar scripts em Python que realizem chamadas de rede para APIs de IA comerciais (OpenAI, Anthropic, Gemini API) com chaves de API gerenciadas pelo script. Toda a inferência de LLM é de responsabilidade da IDE Antigravity.
2. **Daemons de Fila (Redis Streams / Celery):** Está explicitamente fora de escopo qualquer orquestração assíncrona por Redis Streams, Consumer Groups em background ou loops de polling para verificação de tarefas.
3. **Substituição de Ambientes Virtuais Globais:** O `kit-bootstrap.sh` não manipulará o interpretador Python do sistema (`/usr/bin/python3`) nem modificará ambientes gerenciados por `conda` fora do diretório local do projeto.
4. **Remoção de Módulos Legados Não Pertinentes:** A higienização de arquivos legados de testes em `source/tests/` limita-se àqueles que quebram a suite ou referenciam os daemons descontinuados de `sdd-judge-distributed`.

---

## 6. Rastreabilidade Constitucional (Vitalia SDD Principles)

| Princípio | Conformidade na Especificação |
|---|---|
| **P01 (SDD First)** | A feature é 100% especificada e ancorada em artefatos antes de qualquer edição de código produtivo. |
| **P02 (User Value)** | Elimina travamentos de máquina, falsos positivos e retrabalho do desenvolvedor. |
| **P06 (Security & Secrets)** | Proíbe armazenamento de chaves de API em scripts e protege arquivos `.env` preexistentes. |
| **P07 (Privacy & Confidentiality)** | Todo o ciclo de auditoria de tarefas ocorre no perímetro local da IDE, sem envio de código para servidores externos. |
| **P09 (Medical Safety Gate)** | Regras clínicas só são carregadas em projetos com perfil de saúde via Guardian Context Lifting. |
| **P11 (Hardware Agnosticism)** | Não hardcoda modelos; opera nativamente em qualquer máquina suportada pela IDE Antigravity. |
| **P17 (EU AI Act & HITL)** | Obrigatoriedade estrita de geração do `Relatório de inspeção.md` e confirmação no chat antes do carimbo. |
