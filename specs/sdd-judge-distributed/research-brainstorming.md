<!-- research-brainstorming.md | Vitalia SDD v0.6.0 | 16-10-2026 13:58(GMT-04:00) -->

# Registro de Concepção e Brainstorming: Refatoração do Validador de Tarefas e Bootstrap

## 1. Resumo Executivo das Decisões Tomadas

Nesta sessão de brainstorming foi alinhada a substituição do motor adversarial por subprocessos e Redis Streams (que gerou tempestade de eventos, loops cegos e falsos testes) por uma arquitetura nativa no ecossistema da IDE Antigravity, orientada a workflows e com separação estrita de privilégios.

### Decisão 1: Validador Constitucional via Workflow Dedicado (`/vitalia-task-verifier`)
- **Arquitetura:** O julgamento e o debate adversarial não utilizam chamadas REST para APIs externas avulsas nem scripts em background que disputam a VRAM da GPU local (GTX 1060 6GB). Toda a inferência e análise ocorrem **nativamente dentro do ambiente da IDE Antigravity**.
- **Adversarial Red Team:** Para eliminar o viés de confirmação (onde o agente construtor valida a si próprio), o workflow `/vitalia-task-verifier` assume a persona de **Auditor Constitucional Independente (Red Team)**, auditando o `tasks.md` gerado contra `spec.md` e `plan.md`.
- **Handoff em `spec-tasks.toml`:** O `spec-tasks.toml` é desacoplado do hook quebrado de `after` e conclui orientando formalmente o acionamento de `/vitalia-task-verifier`.

### Decisão 2: Regras Constitucionais Dinâmicas via Context Lifting (§11 do Guardian)
- **Zero Regras Engessadas no Prompt:** O arquivo `task-verifier.toml` não declara princípios nem regras de domínio de forma fixa no texto do prompt.
- **Oráculo Dinâmico em `tmp/`:** O hook runner invoca `guardian_context.py` (§11), que extrai do perfil ativo e de `.vitalia/feature.json` a constituição e os domínios pertinentes, injetando-os dinamicamente no arquivo temporário `~/.vitalia/tmp/task-verifier_<timestamp>.json`.
- **Avaliação Contextual:** A IA da IDE consome o campo `guardian_json.sources.constitution.principles` e avalia as tarefas conforme o seu domínio real:
  - Tarefas clínicas/biomarcadores $\rightarrow$ auditadas sob **P09 (Medical Safety Gate)** e **P07**.
  - Tarefas de infraestrutura/IA $\rightarrow$ auditadas sob **P11 (Hardware Agnosticism)**.
  - Tarefas de interface visual $\rightarrow$ auditadas sob **P02** e **P05** sem falsas acusações de credenciais (P06).
- **Proteção de PII/PHI:** Toda a validação opera no perímetro local da sessão interativa da IDE do desenvolvedor, eliminando qualquer trânsito de dados de saúde ou identificadores para provedores externos.

### Decisão 3: `kit-bootstrap.sh` Portável, Agnóstico e com `.venv` no Projeto Local
- **Destino do `.venv`:** O ambiente virtual `.venv` criado ou atualizado pelo script pertence **estritamente ao projeto local** (`./.venv`), onde `requirements.txt` é instalado. A pasta global `~/.vitalia/` não hospeda o virtualenv do projeto.
- **Origem Flexível com Fallback Interativo:** O script aceita argumento de diretório de origem (`bash kit-bootstrap.sh [origem]`), detecta pastas padrão (`./source` ou `./kit-global`) e, caso não encontre, solicita o caminho interativamente ao usuário.
- **Sincronização Limpa:** Realiza `rsync` agnóstico dos arquivos novos e editados para `~/.vitalia/`, protegendo a memória (`~/.vitalia/memory/`) e configurações locais.
- **Import Universal:** Configura o link `.pth` no virtualenv do projeto local apontando para `~/.vitalia/src`, eliminando erros de `ModuleNotFoundError: No module named 'source'` em qualquer máquina Linux/macOS.

---

## 2. Rastro de Pesquisa e Grounding (P03)

| # | Afirmação Técnica | Verificado? | Fonte / Evidência | Data |
|---|---|:---:|---|:---:|
| 1 | Multi-Agent Debate e Red Team reduzem confirmation bias em geração de código e tarefas | Sim | Surveys em *Awesome-Agent-as-a-Judge* e repositório *Argus-Framework/argus-ai-debate* | 16-10-2026 |
| 2 | Modelos locais de 3B em GPU de 6GB sofrem com concorrência simultânea de múltiplos workers assíncronos | Sim | Telemetria do container `ai-control_ollama` e probe da auditoria em `kit_judge_audit.md` | 16-10-2026 |
| 3 | Preservação de PII/PHI exige que dados clínicos não sejam enviados para APIs cloud sem BAA/DPA | Sim | Art. 14 EU AI Act, HIPAA Safe Harbor e Artigo P07/P09 da Constituição Vitalia SDD | 16-10-2026 |
| 4 | O Kit Vitalia v0.6.0 já implementa injeção de constituição via §11 Context Lifting em `guardian_context.py` | Sim | Código-fonte em `source/src/hooks/guardian_context.py` e `AGENTS.md` | 16-10-2026 |
| 5 | Virtualenvs Python aceitam arquivos `.pth` em `site-packages` para resolução agnóstica de pacotes | Sim | Documentação oficial Python `site.py` / standard library | 16-10-2026 |

---

## 3. Próximos Passos no Pipeline SDD

Conforme o protocolo do Kit Vitalia, o ciclo de concepção está concluído com sucesso e o handoff formal deve ser realizado.

**Ação recomendada ao desenvolvedor:**
Executar `/vitalia-spec-specify` para formalizar a especificação funcional (`spec.md`) desta refatoração com base nas decisões deste documento.
