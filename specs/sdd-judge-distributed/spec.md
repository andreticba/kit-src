<!-- spec.md | Vitalia SDD v0.6.0 | 15-10-2026 20:18(GMT-04:00) -->
# Especificação de Funcionalidade: SDD Judge Distribuído & Multi-Agente

**Data:** 15-10-2026 20:18(GMT-04:00)  
**Feature:** `sdd-judge-distributed`  
**Status:** DRAFT (Submetido a Validação Constitucional)  
**Artefatos Relacionados:**
- [research-brainstorming.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-distributed/research-brainstorming.md)
- [kit_routing_audit.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-distributed/kit_routing_audit.md)
- [architecture-diagrams.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-distributed/architecture-diagrams.md)

---

## 1. Contexto e Objetivo (O Quê e Por Quê)

O `sdd_judge.py` atua como o gate constitucional automatizado do Vitalia Kit, auditando a conformidade dos artefatos SDD (`spec.md`, `plan.md`, `tasks.md`). Contudo, a estratégia anterior de avaliação atômica 1-a-1 de tarefas no `tasks.md` sofria de **isolamento descontextualizado**: cada linha de tarefa era enviada isolada ao LLM, levando modelos compactos ($\le 4B$) a alucinarem violações de regras globais (ex: falso bloqueio de P05 alegando falta de teste na mesma linha e falso alarme de segredos P06 em componentes de interface visual). Além disso, verificou-se que modelos $\ge 7B$ sofrem transbordo de CPU na GPU local de 6GB, arrastando o tempo de auditoria para quase 40 minutos.

O objetivo desta funcionalidade é implementar uma **arquitetura de julgamento distribuída e orientada a eventos**, baseada em um **Envelope JSON Antialucinação**, orquestração via **Redis Streams com Consumer Groups**, máquina de estados finita com limite estrito de **5 ciclos de contestação/refatoração**, **Escalada HITL determinística com Dossiê Consolidado**, e gravação atômica final em disco. A solução desacopla modelos através de **Perfis de Capacidade Abstratos**, garantindo velocidade ($< 3s$ por tarefa), precisão constitucional e proteção da cota de tokens do desenvolvedor.

---

## 2. Requisitos Funcionais (FR-xxx)

### FR-001: Extração Estrutural de Tarefas com Envelope Antialucinação
- **Descrição:** O sistema **MUST** realizar o parse sintático do arquivo `tasks.md` e gerar para cada tarefa um Envelope JSON estruturado contendo metadados da User Story pai, fase de entrega, tipo de componente (ex: `frontend_ui`, `backend_service`), referências explícitas a tarefas de teste predecessoras e flags de isenção de regras irrelevantes.
- **Impacto ao Usuário (P02):** Elimina 100% dos falsos bloqueios de P05 (*Test-First*) e falsos alarmes de P06 (*Secrets*) em componentes visuais, poupando o desenvolvedor de reescrever tarefas válidas ou sofrer interrupções espúrias.
- **Governança e Privacidade (P07, P09, P17):** Esta funcionalidade constitui ferramenta interna de desenvolvimento de software; não manipula dados clínicos, biomarcadores ou diagnósticos (Medical Safety Gate P09 não ativado). Em aderência a P07 e P17, o parser processa apenas metadados técnicos de tarefas e código-fonte, sem armazenar dados pessoais (PII/PHI).

### FR-002: Persistência de Estado e FSM em Redis Hashes
- **Descrição:** O sistema **MUST** criar e gerenciar uma máquina de estados finita (FSM) para cada tarefa em chaves Redis `sdd:task:{feature}:{task_id}`, transitando deterministicamente entre os estados `INGESTED`, `A_ANALISAR`, `REPROVADA`, `REFATURANDO`, `APROVADA` e `ESCALADA_HITL`.
- **Impacto ao Usuário (P02):** Garante visibilidade e rastreabilidade total do ciclo de vida das tarefas em tempo real, permitindo retomadas resilientes sem perda de contexto em caso de falha de conexão.
- **Governança e Privacidade (P07, P09, P17):** Os hashes no Redis armazenam exclusivamente identificadores técnicos e logs sintáticos de auditoria; nenhum dado pessoal sensível é trafegado ou persistido (P07). Não há tomada de decisão médica automatizada (P09).

### FR-003: Orquestração Assíncrona via Redis Streams e Consumer Groups
- **Descrição:** O sistema **MUST** orquestrar a distribuição de trabalho através do Stream `sdd:events:{feature}`, operando com três grupos de consumidores isolados: `juiz_group` (Agente Juiz), `contesta_group` (Agente Contestador de triagem rápida) e `refatura_group` (Agente Refaturador).
- **Impacto ao Usuário (P02):** Acelera o tempo global de auditoria da feature de dezenas de minutos para menos de 2 minutos, desacoplando a inferência de regras da reconciliação semântica.
- **Governança e Privacidade (P07, P09, P17):** Os eventos no stream limitam-se ao pipeline de software e ferramentas do desenvolvedor, em estrita conformidade com limites de governança (P01) e sem envolvimento de dados de saúde de pacientes (P09).

### FR-004: Protocolo de Escalada HITL com Limite Estrito de 5 Ciclos
- **Descrição:** Cada tarefa **MUST** manter um contador atômico `cycle_count`. Caso o debate entre contestação e refatoração atinja 5 ciclos sem consenso, o sistema **MUST** suspender a tarefa, transicionar para `ESCALADA_HITL` e emitir um Dossiê Consolidado de Divergências com ações rápidas de 1 comando (1: Manter original, 2: Adotar última refatoração, 3: Ajuste manual).
- **Impacto ao Usuário (P02):** Elimina o risco de deadlocks e loops infinitos entre agentes, garantindo que o desenvolvedor seja acionado apenas quando houver impasse semântico genuíno, com todo o histórico comparativo mastigado para decisão instantânea.
- **Governança e Privacidade (P07, P09, P17):** Implementa o princípio de supervisão humana efetiva (*Human Oversight* - EU AI Act Art. 14 / P17) em sistemas agênticos, garantindo que decisões controversas de engenharia nunca sejam adotadas sem consentimento do operador humano.

### FR-005: Transação em Memória com Flush Atômico Final no Disco
- **Descrição:** Durante todo o processo de auditoria e refatoração, o arquivo físico `tasks.md` no disco **MUST** permanecer inalterado. O Agente Juiz **MUST** realizar o flush atômico para o disco apenas quando 100% das tarefas da feature estiverem no estado `APROVADA`.
- **Impacto ao Usuário (P02):** Protege a base de código do desenvolvedor contra corrupção parcial de arquivos no disco durante a execução do comando, mantendo o workspace estável para rollback.
- **Governança e Privacidade (P07, P09, P17):** Garante a integridade e rastreabilidade dos artefatos do pipeline SDD (P01), assegurando que o código persistido reflita integralmente tarefas aprovadas sem divergência.

### FR-006: Roteamento Agnóstico por Perfis de Capacidade (.env — P11)
- **Descrição:** O sistema **MUST** desacoplar o código de nomes fixos de modelos de IA, roteando os agentes com base em três perfis configuráveis no `.env`: `VITALIA_AUDITOR_MODEL` (triagem rápida em VRAM), `VITALIA_REFACTOR_MODEL` (especialista em código) e `VITALIA_ARBITER_MODEL` (árbitro de desempate).
- **Impacto ao Usuário (P02):** Garante interoperabilidade universal de hardware, permitindo que o desenvolvedor execute o pipeline localmente em GPUs de 6GB ou escale para servidores dedicados sem alterar uma única linha de código.
- **Governança e Privacidade (P07, P09, P17):** Assegura que o desenvolvedor possa optar por inferência 100% local (Ollama) para soberania total de dados e código proprietário (P07, P11), eliminando a saída forçada de dados para provedores externos.

### FR-007: Isolamento de API e Constrained Grammar Decoding
- **Descrição:** O sistema **MUST** invocar os motores de inferência via chamadas REST limpas sem contaminação de ferramentas externas (`tools: []`), aplicando Constrained Grammar Decoding (`format: json_schema`) obrigatório.
- **Impacto ao Usuário (P02):** Previne desvios causados por falsos disparos de ferramentas de chat e anula alucinações de recusa, garantindo vereditos técnicos estruturados em 100% das chamadas.
- **Governança e Privacidade (P07, P09, P17):** Imposição de contratos formais de schema na saída de modelos previne vulnerabilidades de injeção indireta de prompt e saídas corrompidas (OWASP LLM01 / P12).

### FR-008: Segregação de Camadas por Cota de Tokens
- **Descrição:** O sistema **MUST** segregar os domínios de execução: o time de agentes multidisciplinares de engenharia (`Master AI-Control`, `Django-Stark`, `React-Vinci`, etc.) atua nativamente dentro do ambiente interativo da IDE Antigravity, enquanto as chamadas de API do Gemini ou Ollama local são dedicadas exclusivamente à validação constitucional sintética do `sdd_judge`.
- **Impacto ao Usuário (P02):** Maximiza a economia financeira e preserva o desenvolvedor contra esgotamento de cotas de chaves de API, alocando a cota ampla da IDE para engenharia pesada e a cota de API estritamente para auditorias de conformidade.
- **Governança e Privacidade (P07, P09, P17):** Otimiza a separação de privilégios e responsabilidades (P01), assegurando que o portão de governança constitucional atue como árbitro independente e isolado das personas construtoras.

---

## 3. Requisitos Não-Funcionais (Restrições Técnicas)

- **RNF-001 (Latência de Triagem):** O tempo de processamento do Agente Contesta para cada tarefa em modelo local de triagem ($\le 4B$) na GPU NVIDIA GTX 1060 (6GB) **MUST** ser inferior a 3.0 segundos.
- **RNF-002 (Ocupação de VRAM e Zero CPU Offloading):** O modelo local de triagem alocado em `VITALIA_AUDITOR_MODEL` **MUST** rodar 100% na VRAM (consumo $\le 3.5$ GB com KV Cache), com zero camadas em CPU RAM.
- **RNF-003 (Ciclo de Vida do Redis):** Todas as chaves e streams criados sob o namespace `sdd:*` **MUST** possuir TTL automático de 24 horas para auto-higienização da memória.
- **RNF-004 (Aderência Constitucional):** Nenhuma tarefa do `tasks.md` pode ser aprovada sem validação expressa contra os princípios invioláveis P01 (*SDD Pipeline*), P05 (*Test-First*) e P06 (*Secrets*).

---

## 4. Histórias de Usuário (User Stories)

### US1: Auditoria Rápida e Fidedigna de Tarefas sem Falsos Positivos
**Como um** desenvolvedor utilizando o Vitalia Kit em hardware local com GPU de 6GB,  
**eu quero** que o `sdd_judge` audite o `tasks.md` contextualizando cada tarefa com sua User Story e dependências,  
**para que** tarefas de implementação de código ou componentes visuais não sejam bloqueadas injustamente por falta de contexto.

### US2: Resolução Autônoma e Escalada Human-in-the-Loop em Impasses
**Como um** desenvolvedor focado na entrega da feature,  
**eu quero** que tarefas controvertidas sejam automaticamente refatoradas pelo time de agentes até 5 vezes e, se o impasse persistir, escaladas com um dossiê comparativo,  
**para que** eu nunca fique preso em loops infinitos e possa arbitrar em 1 segundo com clareza absoluta.

### US3: Segurança de Workspace e Preservação de Cotas
**Como um** Tech Lead gerenciando recursos de projeto,  
**eu quero** que as mutações ocorram em memória no Redis até a aprovação total e que a cota da API externa seja usada apenas para vereditos finais,  
**para que** o arquivo físico do projeto permaneça seguro contra corrupções e a cota de API não se esgote prematuramente.

---

## 5. Critérios de Aceite (Acceptance Scenarios)

### Cenário 1: Avaliação de Tarefa de Implementação com Teste Predecessor (P05)
- **Dado que** o arquivo `tasks.md` contém a tarefa de teste `T019 [US2] Criar testes unitários para Modal.tsx` e a tarefa de implementação `T020 [US2] Implementar Modal.tsx`,
- **Quando** o parser estrutural extrair as tarefas e gerar o Envelope Antialucinação,
- **Então** o envelope de `T020` deve declarar explicitamente `predecessor_tests: ["T019"]` e `P05_test_first: "Satisfeito"`,
- **E** o Agente Contesta deve emitir veredito `PASS` para P05 sem exigir que `T020` declare testes em sua própria linha.

### Cenário 2: Isenção de Risco de Segredos em Componentes Visuais (P06)
- **Dado que** uma tarefa descreve a criação de um componente puro de interface `src/components/forms/Modal.tsx`,
- **Quando** o Agente Contesta avaliar o requisito de segurança de credenciais (P06),
- **Então** a flag de escopo `exempt_rules: ["P06"]` deve suprimir qualquer falsa acusação de vazamento de segredos de backend, aprovando a tarefa.

### Cenário 3: Escalada Determinística no 5º Ciclo de Reprovação
- **Dado que** uma tarefa controversa foi rejeitada pelo Agente Contesta e alterada pelo Agente Refatura por 5 iterações consecutivas (`cycle_count == 5`),
- **Quando** o Agente Juiz verificar o contador atômico no Redis Hash,
- **Então** a tarefa deve ser transicionada imediatamente para o estado `ESCALADA_HITL`,
- **E** o sistema deve renderizar o Dossiê Consolidado de Divergências exibindo a tabela dos 5 ciclos e aguardando a decisão do operador humano.

### Cenário 4: Flush Atômico Final no Disco
- **Dado que** 42 das 43 tarefas de uma feature foram aprovadas e 1 tarefa ainda está em refatoração,
- **Quando** inspecionado o sistema de arquivos,
- **Então** o arquivo físico `tasks.md` no disco deve permanecer idêntico ao original sem modificações parciais,
- **E** somente quando a 43ª tarefa atingir `APROVADA`, o Agente Juiz deve realizar a gravação atômica completa no arquivo físico.

---

## 6. Fora do Escopo (Out of Scope)

- Modificação ou reescrita do dispatcher de skills `vitalia-route.toml` (documentada na auditoria e diferida para a feature de manutenção do Kit).
- Criação de interface gráfica desktop para visualização de filas Redis (o controle é via CLI/Terminal e logs de sessão).
- Treinamento ou fine-tuning de novos pesos de modelos LLM (utiliza-se modelos abertos já consolidados no ecossistema Ollama/HuggingFace).

---

## 7. Suposições Verificadas (Grounding P03)

- **"Ollama Native JSON Schema (`format: json`)"**: verificado na documentação oficial da API Ollama (https://ollama.com/blog/structured-outputs) em 15-10-2026.
- **"Redis Streams Consumer Groups (`XREADGROUP`, `XACK`, `XCLAIM`)"**: verificado na documentação oficial do Redis (https://redis.io/docs/latest/develop/data-types/streams/) em 15-10-2026.
- **"Qwen2.5-Coder 3B VRAM Footprint (< 2.0 GB em Q4_K_M)"**: verificado nos registros técnicos do QwenLM e nos logs do container `ai-control_ollama` em 15-10-2026.
- **"CPU Offloading Bottleneck em GPUs Pascal 6GB"**: medido diretamente nos logs do `ai-control_ollama` com penalidade de 3.96 t/s para modelos $\ge 7B$ em 15-10-2026.
