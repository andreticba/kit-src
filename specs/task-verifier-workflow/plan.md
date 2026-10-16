<!-- plan.md | Vitalia SDD v0.6.0 | 16-10-2026 16:30(GMT-04:00) -->

# Implementation Plan: Workflow de Verificação Constitucional & Universal Bootstrap

**Branch**: `task-verifier-workflow` | **Data**: 16-10-2026 16:30(GMT-04:00) | **Spec**: [spec.md](file:///home/andre/projetos/assistidos/kit_src/specs/task-verifier-workflow/spec.md) | **Research**: [research.md](file:///home/andre/projetos/assistidos/kit_src/specs/task-verifier-workflow/research.md)

---

## 1. Summary

Implementação da arquitetura determinística de validação constitucional de tarefas do Vitalia SDD Kit (`task-verifier-workflow`) e do instalador universal `kit-bootstrap.sh`:
1. **Sub-Agente Red Team na IDE:** Auditoria adversarial nativa na IDE Antigravity sem chamadas REST externas ou daemons pesados, eliminando exaustão de VRAM na GPU local (P11).
2. **Context Lifting (§11):** Injeção dinâmica de regras da constituição podada em `~/.vitalia/tmp/task-verifier_*.json`.
3. **HITL Gate Soberano com Dossiê Físico:** Geração de `specs/{feature}/Relatório de inspeção.md` e confirmação mandatória no chat antes de qualquer carimbo (P17).
4. **Carimbo Constitucional Atômico e Backup Preventivo:** Transação atômica em disco criando `tasks.md.bak` e gravando o carimbo de conformidade em `tasks.md`.
5. **Desacoplamento de `spec-tasks`:** Remoção do hook pós-execução e handoff formal para `/vitalia-task-verifier`.
6. **Universal Bootstrap & Imports:** `kit-bootstrap.sh` provisionando `.venv` local no projeto (`./.venv`), resolvendo imports via `kit_env_bootstrap.py`, com salvaguardas para `.env` e `requirements.txt`.

---

## 2. Technical Context & Verificação Externa (P03)

* **Linguagem & Runtime:** Python 3.10+ (compatibilidade estrita com 3.10 a 3.14).
* **Dependências & Protocolo de Verificação Externa (P03):**
  * `kit_env_bootstrap.py`: Resolução dinâmica de `project_root`, `.venv` e injeção em `sys.path`. Verificado em `source/src/kit_env_bootstrap.py`.
  * `guardian_context.py`: Compilação de stubs Context Lifting (§11). Verificado em `source/src/hooks/guardian_context.py`.
  * `sdd_judge.py`: Gatekeeper constitucional de conformidade SDD. Verificado em `source/src/hooks/sdd_judge.py`.
  * `bash`: Shell scripting agnóstico e universal. Verificado em [GNU Bash Manual](https://www.gnu.org/software/bash/manual/).
* **Infraestrutura & Isolamento (P11):** `.venv` exclusivamente local em `./.venv`. Zero dependência de venvs em `~/.vitalia/`.
* **Segurança & Segredos (P06):** Preservação de arquivos `.env` preexistentes via backup `.bak` e merge aditivo sem sobrescrita.

---

## 3. Constitution Check (Auditoria Pré-Implementação)

| Princípio | Status | Evidência / Salvaguarda no Plano |
| :--- | :---: | :--- |
| **P01 (SDD Inviolability)** | **PASS** | Rastreabilidade total derivando de `spec.md` (FR-001 a FR-008) e `research.md`. |
| **P02 (User Value)** | **PASS** | `tasks.md` intacto até confirmação explícita no chat; zero corrupção ou sobrescrita. |
| **P03 (External Grounding)** | **PASS** | Ferramentas do Kit e bibliotecas verificadas e fundamentadas em `research.md`. |
| **P04 (Timestamp GMT-04:00)** | **PASS** | Cabeçalho canônico `16-10-2026 16:30(GMT-04:00)` presente em todos os artefatos. |
| **P06 (Secrets Protection)** | **PASS** | Backup preventivo `.env.bak` e preservação integral de credenciais prévias. |
| **P07 (Privacy & Confidentiality)** | **PASS** | Execução 100% no perímetro local da IDE Antigravity; sem envio de dados para nuvem. |
| **P11 (Hardware Agnosticism)** | **PASS** | Sem modelo ou path hardcoded; inferência na IDE e paths dinâmicos via `kit_env_bootstrap.py`. |
| **P15 (Observability)** | **PASS** | Dossiê formal em `specs/{feature}/Relatório de inspeção.md` para auditoria perene. |
| **P16 (Mermaid Rigor)** | **PASS** | Sintaxe estrita com rótulos entre aspas duplas `""` em `architecture-diagrams.md`. |
| **P17 (HITL Gate Soberano)** | **PASS** | Carimbo só é aplicado após apresentação do relatório e aprovação textual no chat. |

---

## 4. Technical Decisions (ADRs Fundamentadas em research.md)

* **ADR-001: Sub-Agente Red Team Nativo na IDE Antigravity** — Execução dentro da sessão da IDE sem chamadas REST externas ou daemons de background, eliminando exaustão de VRAM na GPU local (P11). Grounding: [research.md ADR-001](file:///home/andre/projetos/assistidos/kit_src/specs/task-verifier-workflow/research.md).
* **ADR-002: Injeção Dinâmica via Guardian §11 Context Lifting** — Regras constitucionais injetadas em runtime em `~/.vitalia/tmp/task-verifier_*.json` a partir do preset ativo do projeto, sem regras estáticas no TOML. Grounding: [research.md ADR-002](file:///home/andre/projetos/assistidos/kit_src/specs/task-verifier-workflow/research.md).
* **ADR-003: Dossiê Físico `Relatório de inspeção.md` e HITL Gate Mandatório** — Auditoria gera obrigatoriamente `Relatório de inspeção.md`. O carimbo no `tasks.md` requer aprovação textual explícita no chat (P17). Grounding: [research.md ADR-004](file:///home/andre/projetos/assistidos/kit_src/specs/task-verifier-workflow/research.md).
* **ADR-004: Carimbo Constitucional Atômico e Backup Preventivo (`tasks.md.bak`)** — Cópia de segurança criada antes de qualquer edição; carimbo `<!-- constitutional-status: APPROVED -->` destrava `/vitalia-spec-implement`. Grounding: [research.md ADR-004](file:///home/andre/projetos/assistidos/kit_src/specs/task-verifier-workflow/research.md).
* **ADR-005: Desacoplamento e Handoff Formal em `spec-tasks`** — Remoção do hook síncrono `[hooks].after` em `spec-tasks.toml` e handoff explícito para o comando `/vitalia-task-verifier`. Grounding: [research.md ADR-004](file:///home/andre/projetos/assistidos/kit_src/specs/task-verifier-workflow/research.md).
* **ADR-006: Universal Bootstrap com `.venv` Local e `kit_env_bootstrap.py`** — Script `kit-bootstrap.sh` cria `.venv` na raiz do projeto local (`./.venv`) e mapeia paths dinamicamente via `kit_env_bootstrap.py`. Grounding: [research.md ADR-005](file:///home/andre/projetos/assistidos/kit_src/specs/task-verifier-workflow/research.md).
* **ADR-007: Salvaguardas Não-Destrutivas contra Colisão de `requirements.txt` e `.env`** — Backups preventivos `.bak`, instalação em camadas para dependências e preservação integral de credenciais prévias em `.env`. Grounding: [research.md ADR-005](file:///home/andre/projetos/assistidos/kit_src/specs/task-verifier-workflow/research.md).

---

## 5. Project Structure & Affected Files

* `specs/task-verifier-workflow/`: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/` e `checklists/`.
* `source/extensions/`: `spec-tasks.toml` (desacoplamento hook) e `task-verifier.toml` (Context Lifting §11).
* `source/src/`: `kit_env_bootstrap.py` e hooks `guardian_context.py`, `sdd_judge.py`.
* `source/`: `kit-bootstrap.sh` (instalador universal) e `config/requirements-kit.txt`.

---

## 6. Phase Overview

* **Phase 1: Setup & Limpeza:** Higienização de artefatos descontinuados em `source/src/judge/` e isolamento de dependências.
* **Phase 2: Universal Bootstrap:** Atualização de `kit-bootstrap.sh` (`.venv` local, salvaguardas `.bak` e `kit_env_bootstrap.py`).
* **Phase 3: Workflow task-verifier:** Desacoplamento de `spec-tasks.toml`, criação de `task-verifier.toml` e Sub-Agente Red Team com gate HITL.
* **Phase 4: Validação & Sincronização:** Testes integrados no `.venv` local e sincronização final com `~/.vitalia/`.
