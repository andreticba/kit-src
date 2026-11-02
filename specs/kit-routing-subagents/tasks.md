<!-- tasks.md | Vitalia SDD v0.6.0 | 20-10-2026 09:50(GMT-04:00) -->
> **tasks.md | Vitalia SDD v0.6.0 | 20-10-2026 09:50(GMT-04:00)**
<!-- constitutional-status: APPROVED | auditor: red-team-vitalia | timestamp: 2026-10-18T11:11:00-04:00 | report: Relatório de inspeção.md -->
# Tasks: kit-routing-subagents

**Spec**: [spec.md](file:///home/andre/projetos/assistidos/kit_src/specs/kit-routing-subagents/spec.md) | **Plan**: [plan.md](file:///home/andre/projetos/assistidos/kit_src/specs/kit-routing-subagents/plan.md)
**Gerado em**: 18-10-2026 11:10(GMT-04:00)

---

## MVP Scope

> Implementar **Phase 1 + Phase 2 + Phase 3 (US1)** entrega produto funcionando.
> Phases adicionais são incrementos opcionais.

---

## Phase 0: Grounding & Environment

*Verificações de ambiente e grounding ANTES de qualquer implementação. Sem label de US.*

- [X] T000-A Ativar ambiente virtual python em `.venv/bin/activate`
- [X] T000-B Verificar versão do interpretador Python em `.venv/bin/python`
- [X] T000-C Verificar dependências instaladas no repositório em `requirements.txt`
- [X] T000-D Verificar biblioteca externa jsonschema no venv em `.venv/lib/python3.14/site-packages/jsonschema`
- [X] T000-E Verificar integridade e compatibilidade de dependências em `pyproject.toml`

---

## Phase 1: Setup

*Inicialização do ambiente e persistência local. Sem label de US.*

- [X] T001 Criar diretório seguro de handoffs locais em `.vitalia/memory/data_storage/handoffs/.gitkeep`
- [X] T002 [P] Configurar exclusão de payloads de handoff em `.gitignore`
- [X] T003 [P] Criar fixtures com campo direction e nomenclatura semântica em `tests/fixtures/handoff_valid.json`

---

## Phase 2: Foundational

*Dependências compartilhadas da biblioteca e CLI de handoff. Sem label de US.*

- [X] T004 Implementar funções core create validate consume e latest com direction e atomicidade em `source/src/vitalia_handoff.py`
- [X] T005 [P] Implementar comandos da interface CLI com flag direction em `source/src/vitalia_handoff.py`
- [X] T006 [P] Criar testes unitários e validação de latência pré-hook em `tests/unit/test_vitalia_handoff.py`

---

## Phase 3: User Story 1 — Transição Fluida e Determinística entre Concepção e Roteamento

**Story Goal**: Permitir que o Brainstorming gere síntese Markdown e handoff progressivo, e que o dispatcher vitalia-route despache para especialistas antes de formalizar a spec.
**Independent Test**: Executar ideação no Brainstorming, gerar handoff forward, despachar via vitalia-route e validar consumo atômico.
**Referência**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006

- [X] T007 [US1] Adicionar validação pré-hook de handoff com verificação de direction em `source/src/vitalia_hook_runner.py`
- [X] T008 [P] [US1] Atualizar prompt do supervisor socrático com síntese Markdown e handoff forward em `source/extensions/brainstorming.toml`
- [X] T009 [P] [US1] Atualizar prompt do despachante oficial com consumo de sources equalizadas e despacho de especialistas em `source/extensions/vitalia-route.toml`
- [X] T010 [US1] Integrar ingestão de session_context.handoff no motor de contexto `source/src/hooks/guardian_context.py`
- [X] T011 [P] [US1] Criar testes de integração do fluxo Brainstorming para Route em `tests/integration/test_brainstorming_to_route_flow.py`

---

## Phase 4: User Story 2 — Escalação Segura quando Agentes Especialistas Extrapolam Domínio

**Story Goal**: Interromper execuções com desvio arquitetural, gerar divergence JSON e handoff reverso forçando retorno seguro ao Brainstorming com soberania HITL.
**Independent Test**: Simular desvio de escopo no executor e validar gravação de divergence JSON e handoff com direction reverse.
**Referência**: FR-007

- [X] T012 [P] [US2] Incluir trava de escalação invertida e gravação de divergence JSON em `source/extensions/spec-implement.toml`
- [X] T013 [P] [US2] Incluir trava de escalação invertida e suspensão de sessão em `source/extensions/pair.toml`
- [X] T014 [US2] Criar testes unitários para o protocolo de escalação invertida em `tests/unit/test_reverse_escalation_protocol.py`

---

## Phase 5: User Story 3 — Catálogo Íntegro, Nomenclatura Padronizada e Equalização de Tokens

**Story Goal**: Saneamento do catálogo com status active/planned, cadastro dos 6 especialistas do AI-Control, correção de prefixo no instalador e equalização adaptativa no Guardian.
**Independent Test**: Executar instalador sem gerar duplicações vitalia-vitalia e testar Guardian com cotas diferenciadas por hardware profile.
**Referência**: FR-008, FR-009, FR-010, FR-011

- [X] T015 [P] [US3] Atualizar status dos agentes e cadastrar equipe AI-Control em `source/profiles/agents_catalog.yaml`
- [X] T016 [P] [US3] Atualizar schema de validação do catálogo em `source/config/schemas/agents_catalog.schema.json`
- [X] T017 [P] [US3] Corrigir derivação de nomes de skills com regex sed no instalador `source/bin/install-project`
- [X] T018 [US3] Implementar equalização adaptativa de tokens por hardware profile em `source/src/hooks/guardian_context.py`
- [X] T019 [P] [US3] Criar testes de validação do catálogo saneado e poda de tokens em `tests/unit/test_catalog_and_token_equalization.py`

---

## Phase 6: Polish & Cross-Cutting

*Qualidade, sincronização com kit global, documentação e conformidade. Sem label de US.*

- [X] T020 Sincronizar arquivos atualizados do kit com a instalação global em `~/.vitalia/`
- [X] T021 Executar instalador local e limpar diretórios duplicados legados em `.agents/skills/`
- [X] T022 [P] Atualizar documentação e contratos no arquivo `README.md`
- [X] T023 Executar suíte completa de testes automatizados com cobertura em `tests/`

---

## Dependency Graph

```
Phase 0 (Grounding) 
  ↓
Phase 1 (Setup) 
  ↓
Phase 2 (Foundational: vitalia_handoff.py)
  ↓
Phase 3 (US1: Handoff Flow) ────┬──── Phase 4 (US2: Reverse Escalation)
                                ↓
                        Phase 5 (US3: Catalog, Installer & Tokens)
                                ↓
                        Phase 6 (Polish & Cross-Cutting)
```

## Parallel Execution

Tasks marcadas com `[P]` operam em arquivos isolados e sem dependências mútuas, podendo ser executadas em paralelo:
- Na **Phase 1**: `T002` e `T003` são paralelizáveis após `T001`.
- Na **Phase 2**: `T005` e `T006` são paralelizáveis após `T004`.
- Na **Phase 3**: `T008`, `T009` e `T011` são paralelizáveis.
- Na **Phase 4**: `T012` e `T013` são paralelizáveis.
- Na **Phase 5**: `T015`, `T016`, `T017` e `T019` são paralelizáveis.
- Na **Phase 6**: `T022` é paralelizável com as validações de documentação.
