<!-- research-brainstorming.md | Vitalia SDD v0.6.0 | 16-10-2026 14:48(GMT-04:00) -->

# Registro de Concepção e Brainstorming: Task Verifier Workflow & Bootstrap Universal

**Feature:** `task-verifier-workflow`  
**Data:** 16-10-2026 14:48(GMT-04:00)  
**Status:** Grounding Proposto para Aprovação do Usuário  
**Documentos Relacionados:**
- [kit_judge_audit.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-distributed/kit_judge_audit.md)
- [architecture-diagrams.md](file:///home/andre/projetos/assistidos/kit_src/specs/task-verifier-workflow/architecture-diagrams.md)
- [research.md](file:///home/andre/projetos/assistidos/kit_src/specs/task-verifier-workflow/research.md)

---

## 1. Contexto Histórico e Lições da Auditoria (Por que recomeçar do zero?)

A tentativa anterior de implementar o `sdd-judge-distributed` via múltiplos processos em background concorrentes operando sobre Redis Streams com modelos SLM locais (3B) falhou na prática, conforme demonstrado na auditoria `kit_judge_audit.md`:

1. **Quebra Estrutural de Imports:** O código foi escrito com `from source.src.judge...`, quebrando imediatamente ao ser instalado na pasta física `~/.vitalia/src/`.
2. **Tempestade de Eventos:** Os três consumer groups liam o mesmo stream sem filtrar `event_type`, gerando escalada para HITL em 0.7s para tarefas perfeitamente válidas.
3. **Cegueira Semântica e Loop Infinito:** O Juiz relia o envelope original e não o texto refatorado, impedindo a convergência.
4. **Falsos Testes Unitários:** Os testes passavam porque mockavam o veredito via banco, sem exercitar a orquestração real.
5. **Violação Constitucional do P11:** Modelos fixos (`qwen2.5-coder:3b`) foram hardcodados no código para forçar testes verdes.
6. **Starvation de Hardware (GTX 1060 6GB):** Forçar 3 daemons concorrentes disputando a VRAM de 6GB gerava saturação e timeouts de socket.

**Decisão Fundamental:** Abandonar a arquitetura assíncrona por Redis Streams para o julgamento de tarefas e transferir a auditoria adversarial para o ambiente nativo da IDE Antigravity através de um workflow dedicado (`/vitalia-task-verifier`).

---

## 2. Decisões Arquiteturais Consolidadas no Brainstorming

### Decisão 1: Validador Constitucional via Workflow Nativo na IDE (`/vitalia-task-verifier`)
- **Zero Chamadas REST a APIs Externas:** Não utiliza scripts fazendo chamadas avulsas para endpoints externos que consomem cotas de faturamento ou expõem chaves de API.
- **Proteção Total de PII/PHI (P07/P09):** Todo o raciocínio ocorre dentro da sessão interativa da IDE Antigravity no ambiente local do desenvolvedor. Nenhum dado de saúde ou credencial trafega para terceiros.
- **Eliminação do Viés de Autocensura (Red Team):** O workflow assume a persona explícita de **Auditor Constitucional Independente (Red Team)**. Ele não herda a defesa do agente gerador; ele audita ativamente para encontrar violações a P00-P17.
- **Relatório de Inspeção e Confirmação Explícita Obrigatória (HITL):** A aprovação e o carimbo constitucional no `tasks.md` **NUNCA** ocorrem de forma silenciosa ou automática. O `/vitalia-task-verifier` gera e apresenta o arquivo `specs/{feature}/Relatório de inspeção.md`. Somente após o desenvolvedor confirmar explicitamente a aprovação no chat, o `tasks.md` recebe o carimbo de conformidade e o backup `tasks.md.bak` é gerado.

### Decisão 2: Regras Constitucionais Vivas via Context Lifting (§11 do Guardian)
- **Zero Regras Estáticas no Prompt:** O arquivo `task-verifier.toml` não contém princípios ou regras de domínio engessadas em texto estático.
- **Oráculo Dinâmico em `~/.vitalia/tmp/`:** O hook runner invoca `guardian_context.py`, que poda e compila os princípios a partir da feature ativa e dos perfis em `profiles/`.
- **Análise Contextual por Domínio:** A IA consome o JSON temporário e avalia cada tarefa estritamente contra as regras incidentes:
  - Domínio Clínico $\rightarrow$ P09 (Medical Safety Gate - status DRAFT e aprovação humana) e P07.
  - Domínio Infraestrutura $\rightarrow$ P11 (Hardware Agnosticism - variáveis de ambiente em vez de literais).
  - Domínio UI / Front-end $\rightarrow$ P02 e P05 (sem falsas acusações de segredos P06).

### Decisão 3: Desacoplamento Limpo em `spec-tasks.toml` e Desbloqueio de `spec-implement`
- Removemos a chamada do hook externo quebrado em `[hooks].after`.
- O relatório de encerramento de `/vitalia-spec-tasks` orienta formalmente:  
  `Próximo passo: /vitalia-task-verifier (Auditoria Constitucional Adversarial)`
- O `/vitalia-spec-implement` valida contratualmente a presença do carimbo de aprovação e do relatório antes de permitir a escrita de código.

### Decisão 4: `kit-bootstrap.sh` Universal, Resolução via `kit_env_bootstrap.py` e Gestão de `.env` e `requirements.txt`
- **Ambiente Python como Primeiro Passo:** O `kit-bootstrap.sh` declara com destaque no terminal que o primeiro passo obrigatório é a configuração do `.venv` e das dependências no projeto local (`./.venv`), nunca em `~/.vitalia/`.
- **Prevenção de Conflitos em `requirements.txt`:** Se o projeto já possuir um `requirements.txt`, o script não realiza merge cego (evitando quebra de versões pinadas pelo desenvolvedor). Ele oferece a opção de instalação segura em camadas (`pip install -r requirements.txt -r requirements-kit.txt`) ou fusão com backup preventivo `.bak`.
- **Gestão Segura de `.env`:** O `.env` recebe o mesmo tratamento protegido. Se já existir, gera backup `.env.bak` e realiza append apenas das chaves ausentes do Kit (`REDIS_URL`, etc.), sem jamais sobrescrever credenciais ou variáveis já configuradas no projeto.
- **Mapeamento Canônico de Imports (`kit_env_bootstrap.py`):** Utiliza a ferramenta já existente no Kit (`source/src/kit_env_bootstrap.py`), que detecta a raiz do workspace, carrega `.env` e injeta dinamicamente o `site-packages` do `.venv` e os scripts do Kit em `sys.path`.
- **Origem Flexível:** Detecta pastas padrão (`./source` ou `./kit-global`) e, se necessário, solicita interativamente o caminho fonte antes de sincronizar para `~/.vitalia/`.

---

## 3. Rastro de Pesquisa e Grounding (P03)

| # | Afirmação Técnica | Verificado? | Fonte / Evidência | Data |
|---|---|:---:|---|:---:|
| 1 | Multi-Agent Debate e Red Team reduzem confirmation bias em geração de código e tarefas | Sim | Surveys em *Awesome-Agent-as-a-Judge* e repositório *Argus-Framework/argus-ai-debate* | 16-10-2026 |
| 2 | Modelos locais de 3B em GPU de 6GB sofrem com concorrência simultânea de múltiplos workers assíncronos | Sim | Telemetria do container `ai-control_ollama` e probe da auditoria em `kit_judge_audit.md` | 16-10-2026 |
| 3 | Preservação de PII/PHI exige que dados clínicos não sejam enviados para APIs cloud sem BAA/DPA | Sim | Art. 14 EU AI Act, HIPAA Safe Harbor e Artigo P07/P09 da Constituição Vitalia SDD | 16-10-2026 |
| 4 | O Kit Vitalia v0.6.0 já implementa injeção de constituição via §11 Context Lifting em `guardian_context.py` | Sim | Código-fonte em `source/src/hooks/guardian_context.py` e `AGENTS.md` | 16-10-2026 |
| 5 | Virtualenvs Python aceitam arquivos `.pth` em `site-packages` para resolução agnóstica de pacotes | Sim | Documentação oficial Python `site.py` / standard library | 16-10-2026 |
