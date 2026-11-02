<!-- plan.md | Vitalia SDD v0.6.0 | 20-10-2026 09:50(GMT-04:00) -->
> **plan.md | Vitalia SDD v0.6.0 | 20-10-2026 09:50(GMT-04:00)**
# Implementation Plan: kit-routing-subagents

**Branch**: `feature/kit-routing-subagents` | **Date**: 18-10-2026 10:50(GMT-04:00) | **Spec**: [spec.md](file:///home/andre/projetos/assistidos/kit_src/specs/kit-routing-subagents/spec.md)
**Governança**: Ferramenta interna de software (medical-gate e constraints clínicos não aplicáveis). Sem segredos em git (P06) e integridade assegurada (P16).

---

## 1. Summary

Roteamento inter-agente local bidirecional determinístico, resolvendo achados A1-A11 de `kit_routing_audit.md`. Institui Ledger Local em `.vitalia/memory/data_storage/handoffs/` (Zero Data Leak) com validação `jsonschema` contra `vitalia-handoff-v1.0.0.json`, desacoplando o Redis. Adota nomenclatura semântica `handoff_<source>_to_<target>_<uuid_8>.json` e o campo `envelope.direction` (`forward`, `reverse`, `fallback`). O `/vitalia-brainstorming` atua como supervisor socrático gerando síntese Markdown editável (HITL), transferindo contexto para o dispatcher `/vitalia-route`. O `/vitalia-route` despacha primeiro para especialistas do catálogo (`active`) e, com a concepção madura (retorno reverso em JSON), orienta `/vitalia-spec-specify`. No fallback Nível 3, preserva contexto via handoff. Executores aplicam trava de escalação invertida em desvios com `divergence_<uuid_8>.json`. Catálogo saneado (`active`/`planned`) com equipe AI-Control. Instalador idempotente e Guardian com equalização (`source_weights`). Antecede o `tasks.md` via `/vitalia-spec-tasks` (P01).

---

## 2. Technical Context

- **Language/Version**: Python 3.11+
- **Primary Dependencies**: `jsonschema >= 4.23.0` (Draft-07), `pyyaml >= 6.0.1`, biblioteca padrão (`os`, `json`, `pathlib`, `uuid`, `hashlib`, `socket`, `datetime`)
- **Storage**: Filesystem local do projeto (`.vitalia/memory/data_storage/handoffs/`)
- **Testing**: `pytest >= 8.3.0` (testes unitários e benchmark < 100ms p95)
- **Target Platform**: Linux / macOS (Agnóstico x86_64/ARM64)
- **Project Type**: CLI & Engine Hooks do Vitalia Kit
- **Performance Goals**: Latência pré-hook < 100ms (p95); equalização até 1000 tokens para local (`lightweight`) e até 4000 tokens para IDE (`frontier`)
- **Constraints**: Sem Redis ativo; zero gravação fora do projeto; sem credenciais em código (`.env` P06); `machine_id` via `VITALIA_MACHINE_NAME` ou `socket.gethostname()` SHA256[:8] (P11).

---

## 3. Constitution Check

- **P01 (SDD Pipeline Inviolability)**: Fluxo obrigatório `spec.md` ➔ `plan.md` ➔ `tasks.md` ➔ `implement`. Precede `tasks.md`; vedada codificação antes de plano e tarefas aprovados.
- **P03 (External Verification Protocol)**: Decisões verificadas em fontes autoritativas em [research.md](file:///home/andre/projetos/assistidos/kit_src/specs/kit-routing-subagents/research.md).
- **P04 (Timestamp GMT-04:00)**: Cabeçalhos, logs e metadados no fuso imutável America/Cuiaba (`GMT-04:00`).
- **P06 (Secrets Never in Git)**: Sem credenciais em código/commits. Configuração via `.env`.
- **P11 (Hardware-Agnostic LLM Routing & Machine Identity)**: `machine_id` derivado de `VITALIA_MACHINE_NAME` ou `socket.gethostname()` SHA256[:8]. Equalização por `hardware_profile`.
- **P15 (Observability & Structured Logging)**: Logs estruturados com rastreabilidade técnica dos eventos e direção.
- **P16 (Artifact Integrity & Defensive Programming)**: Atomicidade no filesystem (`os.replace`) e diagramas defensivos.

---

## 4. Technical Decisions (ADRs)

### ADR: ADR-001 Desacoplamento do Redis e Ledger Local Semântico
- **Escolhido**: Módulo `source/src/vitalia_handoff.py` em `.vitalia/memory/data_storage/handoffs/handoff_<source>_to_<target>_<uuid_8>.json` com `direction`.
- **Verificado em**: https://docs.python.org/3/library/os.html#os.replace e https://json-schema.org em 18-10-2026.
- **Justificativa**: Rastreabilidade visual no filesystem e execução offline sem Redis.
- **Alternativas**: `Redis Streams` (congelado) e nomes opacos `handoff_<uuid>.json` (rejeitados).
- **Governança (P01, P04, P06, P11, P15, P16)**: Sem segredos (P06); `machine_id` via `VITALIA_MACHINE_NAME` / `socket.gethostname()` SHA256[:8] (P11); timestamps GMT-04:00 (P04); atomicidade via `os.replace` (P16).

### ADR: ADR-002 Persistência Segura e Isolamento Zero Data Leak
- **Escolhido**: Confinamento hermético em `.vitalia/memory/data_storage/handoffs/`.
- **Verificado em**: LGPD Art. 11/48 e OWASP LLM07 em 18-10-2026.
- **Justificativa**: Previne vazamento de contexto entre projetos locais.
- **Alternativas**: `/tmp` e `~/.vitalia/tmp` (rejeitados por risco à privacidade).
- **Governança (P01, P04, P06, P11, P15, P16)**: Confinamento sem segredos (P06); isolamento local (P15).

### ADR: ADR-003 Validação Pré-Hook com Schema JSON Formal
- **Escolhido**: Validação estrita via `jsonschema` contra `vitalia-handoff-v1.0.0.json` com `direction`.
- **Verificado em**: https://pypi.org/project/jsonschema/ em 18-10-2026.
- **Justificativa**: Bloqueia payloads inválidos com código 1 antes de atingir o LLM.
- **Alternativas**: Validação ad-hoc e Pydantic v2 (rejeitados por fragilidade).
- **Governança (P01, P04, P06, P11, P15, P16)**: Validação rápida (< 100ms p95); fail-safe (P16).

### ADR: ADR-004 Protocolo de Escalação Invertida e Despacho de Especialistas
- **Escolhido**: Interrupção com `divergence_<uuid_8>.json` e handoff reverso; despacho do route para especialistas antes do pipeline SDD.
- **Verificado em**: EU AI Act Art. 14 (Human Oversight) e Topologia de Transição em 18-10-2026.
- **Justificativa**: Preserva soberania humana (P00/P01). Nenhuma IA altera arquitetura sem HITL; especialistas atuam antes da spec.
- **Alternativas**: Pular direto para `spec-specify` ou alteração autônoma (rejeitadas).
- **Governança (P01, P04, P06, P11, P15, P16)**: Rastreabilidade formal em ADR (`docs/adr/`) e auditoria técnica (P01/P15).

### ADR: ADR-005 Saneamento do Catálogo com Status Operacional e Ingestão AI-Control
- **Escolhido**: Campo `status: "active" | "planned"` no `agents_catalog.yaml` e 6 especialistas AI-Control como `planned`.
- **Verificado em**: Memorando `AI-Control completo.md` e Catálogo Vitalia em 18-10-2026.
- **Justificativa**: Elimina comandos fantasmas, garantindo clareza do que é executável e mapeando roadmap.
- **Alternativas**: Exclusão de agentes conceituais (descartada por apagar visão).
- **Governança (P01, P04, P06, P11, P15, P16)**: Fidedignidade catálogo/código e desacoplamento de hardware (P11).

### ADR: ADR-006 Nomenclatura Idempotente no Instalador e Equalização de Tokens
- **Escolhido**: Regex `sed 's/^vitalia-//'` no `source/bin/install-project` e equalização de cotas (`source_weights`) no Guardian.
- **Verificado em**: Padrões GNU Sed e Context Window Economics em Claude Code e Qwen2.5 em 18-10-2026.
- **Justificativa**: Nomenclatura canônica (`vitalia-*`) e equalização: até 4000 tokens na IDE (`frontier`) e até 1000 tokens no local (`lightweight`).
- **Alternativas**: Limite universal rígido e truncamento cego (rejeitados).
- **Governança (P01, P04, P06, P11, P15, P16)**: Idempotência de build; conformidade P11 e P16.

---

## 5. Phase Overview

- **Phase 1 (Setup)**: Provisionamento de `data_storage/handoffs/` e fixtures do schema com `direction`.
- **Phase 2 (Core Engine)**: Implementação de `source/src/vitalia_handoff.py` com nomenclatura canônica e CLI.
- **Phase 3 (Hooks & Guardian)**: Ingestão de `--handoff` no `vitalia_hook_runner.py` e equalização no `guardian_context.py`.
- **Phase 4 (Workflows & Catálogo)**: Atualização dos TOMLs (`brainstorming`, `vitalia-route`, `spec-implement`, `pair`), `agents_catalog.yaml` e `install-project`.
- **Phase 5 (Tasks & Validação)**: Geração de `tasks.md` via `/vitalia-spec-tasks` e auditoria via `/vitalia-task-verifier`.
