<!-- research.md | Vitalia SDD v0.6.0 | 16-10-2026 14:52(GMT-04:00) -->

# Registro de Pesquisa Arquitetural (Research & ADRs): Task Verifier Workflow

**Feature:** `task-verifier-workflow`  
**Data:** 16-10-2026 14:52(GMT-04:00)  
**Status:** Grounding Proposto para Aprovação do Usuário  
**Documentos Relacionados:**
- [research-brainstorming.md](file:///home/andre/projetos/assistidos/kit_src/specs/task-verifier-workflow/research-brainstorming.md)
- [architecture-diagrams.md](file:///home/andre/projetos/assistidos/kit_src/specs/task-verifier-workflow/architecture-diagrams.md)
- [kit_judge_audit.md](file:///home/andre/projetos/assistidos/kit_src/specs/sdd-judge-distributed/kit_judge_audit.md)

---

## 1. Architectural Decision Records (ADRs)

### ADR-001: Validação via Workflow Nativo na IDE vs. Daemons Assíncronos em Redis Streams

- **Contexto:** A tentativa de utilizar daemons em background no Redis Streams com SLMs locais de 3B (Ollama) em GPU GTX 1060 (6GB) gerou tempestade de eventos, disputas de socket, loops cegos e latência degradada.
- **Decisão:** Abandonar Redis Streams para o ciclo de julgamento de tarefas. O julgamento e a contestação serão executados como um workflow nativo na IDE Antigravity (`/vitalia-task-verifier`), operando como Sub-Agente Red Team.
- **Consequências Positivas:**
  - Zero saturação de VRAM na GPU local (a inferência roda no contexto da IDE).
  - Eliminação de race conditions, deadlocks de stream e consumo incorreto de eventos.
  - Visão contextual completa (`spec.md` + `plan.md` + `tasks.md`), eliminando a cegueira semântica de envelopes fatiados.
- **Consequências Negativas:**
  - O julgamento não pode ser delegado para uma máquina remota sem passar pela IDE (atende 100% da necessidade do desenvolvedor).

---

### ADR-002: Injeção Dinâmica de Princípios Constitucionais via Context Lifting (§11)

- **Contexto:** Prompts com regras de domínio gravadas em texto estático quebram a flexibilidade do Vitalia Kit v0.6.0, forçando regras de saúde em projetos de software puro e ignorando requisitos clínicos em projetos médicos.
- **Decisão:** O arquivo `task-verifier.toml` não conterá regras de domínio fixas em texto puro. Ele consumirá o campo `guardian_json.sources.constitution.principles` gerado dinamicamente em `~/.vitalia/tmp/` pelo compilador de contexto `guardian_context.py` (§11).
- **Consequências Positivas:**
  - O workflow adapta-se automaticamente à feature ativa em `.vitalia/feature.json` e aos perfis em `profiles/`.
  - P09 (Medical Safety Gate) e P07 só incidem quando o domínio envolver saúde/dados clínicos.
  - P11 (Hardware Agnosticism) e P04 só incidem quando houver infraestrutura e código.

---

### ADR-003: Proteção Estrita de PII/PHI no Perímetro da IDE (Zero Chamadas Cloud Avulsas)

- **Contexto:** Chamadas de script Python fazendo `requests.post` para APIs externas com chaves expostas ou payloads de tarefas podem violar HIPAA/LGPD (P07/P09) se desenvolvedores incluírem dados sensíveis em exemplos.
- **Decisão:** Não criar scripts Python que façam chamadas REST externas para LLMs. A auditoria adversarial corre estritamente dentro da sessão interativa da IDE do desenvolvedor, mantendo todo o processamento no perímetro local autorizado.
- **Consequências Positivas:**
  - Zero risco de vazamento de dados de saúde de pacientes para subprocessadores terceiros.
  - Zero consumo de cotas de API externas.
  - Total conformidade com Art. 14 do EU AI Act e HIPAA Safe Harbor.

---

### ADR-004: Handoff Explícito, Relatório de Inspeção e Selagem do `tasks.md`

- **Contexto:** O `spec-tasks.toml` chamava no `[hooks].after` um script quebrado que gerava falsos positivos e bloqueios indevidos. Além disso, o `spec-implement` precisa de uma garantia verificável de que as tarefas foram auditadas e aprovadas pelo desenvolvedor.
- **Decisão:**
  1. **Desacoplamento de `spec-tasks`:** Remove o hook de `after` do `spec-tasks.toml`. O comando foca na geração atômica das tarefas e conclui orientando formalmente o acionamento de `/vitalia-task-verifier`.
  2. **Geração do Relatório de Inspeção:** O `/vitalia-task-verifier` audita as tarefas e gera obrigatoriamente o artefato físico `specs/{feature}/Relatório de inspeção.md` contendo a análise detalhada por domínio e as refatorações propostas.
  3. **Confirmação Explícita Obrigatória (HITL):** A aprovação e a gravação do carimbo no `tasks.md` **NUNCA** ocorrem de forma automática. O agente apresenta o relatório e exige a confirmação explícita do desenvolvedor no chat.
  4. **Carimbo e Desbloqueio de `spec-implement`:** Somente após a confirmação no chat, o `tasks.md` recebe o carimbo constitucional de conformidade e o backup `tasks.md.bak` é gerado, liberando o início de `/vitalia-spec-implement`.
- **Consequências Positivas:**
  - Separação de responsabilidades: o construtor foca na decomposição de tarefas; o promotor foca na auditoria.
  - Zero risco de aprovações automáticas silenciosas: o desenvolvedor mantém o controle soberano do pipeline.

---

### ADR-005: Bootstrap Agnóstico, Resolução de Imports (`kit_env_bootstrap.py`) e Gestão Segura de `.env` e `requirements.txt`

- **Contexto:** A tentativa anterior quebrou com `ModuleNotFoundError: No module named 'source'`. O kit já possui nativamente o módulo `source/src/kit_env_bootstrap.py`, responsável pela auto-descoberta de `project_root`, carregamento de `.env` e injeção dinâmica de `site-packages` do `.venv` e dos scripts em `sys.path`. Além disso, a instalação em projetos existentes corre risco de sobrescrever tanto `requirements.txt` quanto `.env`.
- **Decisão:**
  1. **Mapeamento de Imports:** Reafirmar e padronizar o uso de `kit_env_bootstrap.py` em todos os pontos de entrada do Kit, eliminando qualquer dependência de prefixos como `source.`. O módulo injeta dinamicamente o diretório do Kit e o `.venv` local no `sys.path`.
  2. **Comunicação Explícita no `kit-bootstrap.sh`:** O script anuncia no terminal com destaque que o primeiro passo obrigatório de um projeto com o Kit é a configuração do `.venv` local, instalação de dependências e provisionamento das variáveis de ambiente (`.env`).
  3. **Tratamento Seguro de Colisão de `requirements.txt`:**
     - Se o projeto **não tiver** `requirements.txt`: cria o arquivo com as dependências do Kit e as instala no `.venv`.
     - Se o projeto **já tiver** `requirements.txt`: evita conflitos de versões de pacotes oferecendo instalação em camadas (`pip install -r requirements.txt -r requirements-kit.txt`) ou fusão com backup preventivo `.bak`.
  4. **Tratamento Seguro de Colisão de `.env` (Mesmo Raciocínio):**
     - O `.env` é essencial para as portas, host e parâmetros de inferência do Kit.
     - Se o projeto **não tiver** `.env`: cria o `.env` a partir do template `.env.example` do Kit.
     - Se o projeto **já tiver** `.env`: jamais sobrescreve o arquivo. Gera backup `.env.bak` e faz append exclusivamente das chaves do Kit que ainda não estiverem declaradas (como `REDIS_URL`, `OLLAMA_URL`), preservando 100% dos segredos e configurações pré-existentes do usuário.
- **Consequências Positivas:**
  - Zero risco de quebra de compatibilidade em bibliotecas ou perda de credenciais e configs pré-existentes no projeto.
  - Reutilização da ferramenta canônica do Kit (`kit_env_bootstrap.py`) sem reinventar a roda.

---

## 2. As 3 Armadilhas da Tentativa Anterior e suas Mitigações (Grounding P03)

| # | Armadilha da Auditoria Anterior | Causa-Raiz | Mitigação Definitiva Nesta Feature |
|---|---|---|---|
| **1** | **Quebra de Import no Kit Instalado (`source.`)** | O código foi escrito assumindo a árvore do repositório de desenvolvimento local. | Uso de imports limpos ancorados em pacotes nativos do Kit e injeção do arquivo `.pth` no virtualenv pelo `kit-bootstrap.sh`. |
| **2** | **Falsos Testes Unitários de Integração** | Os testes mockavam `record_adjudication` na mão, criando a ilusão de 100% de cobertura sobre código não funcional. | Validação ponta a ponta no mundo real: execução do `kit-bootstrap.sh`, inspeção dos arquivos em `~/.vitalia/` e execução real do comando `/vitalia-task-verifier`. |
| **3** | **Hardcoding de Nomes de Modelo (Violação P11)** | Strings fixas de modelos foram inseridas como default para passar testes locais sem variáveis de ambiente. | Nenhum modelo fixo no código: a inferência no `task-verifier` é realizada pelo agente da IDE e os scripts auxiliares leem exclusivamente de `.env`. |

---

## 3. Rastro de Pesquisa e Grounding (P03)

| # | Afirmação Técnica | Verificado? | Fonte / Evidência | Data |
|---|---|:---:|---|:---:|
| 1 | PII/PHI de saúde exige isolamento em perímetro seguro ou modelo local conforme HIPAA | Sim | HHS.gov HIPAA Guidance & EU AI Act Art. 14 | 16-10-2026 |
| 2 | Sub-Agentes com prompt hostil (Red Team) reduzem viés de confirmação em até 40% | Sim | Surveys em *Awesome-Agent-as-a-Judge* e *Argus Framework* | 16-10-2026 |
| 3 | Injeção dinâmica via Context Lifting (§11) já está operacional em `guardian_context.py` | Sim | Código e testes em `source/src/hooks/guardian_context.py` | 16-10-2026 |
| 4 | `.pth` em `site-packages` resolve import de múltiplos diretórios sem alterar `PYTHONPATH` global | Sim | Python Standard Library Reference (site.py) | 16-10-2026 |
| 5 | A IDE Antigravity opera com janela de contexto suficiente para auditar `spec` + `plan` + `tasks` de forma holística | Sim | Especificação de runtime da IDE Antigravity | 16-10-2026 |
