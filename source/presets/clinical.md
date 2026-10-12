<!-- medical-gate.spec.md | Atualizado em: 26-06-2026 12:08:28(GMT-04:00) -->
<!-- TEMPLATE — copie para specs/[nome-da-feature].spec.md antes de editar -->

---
status: DRAFT
risco_clinico: MEDIUM    # LOW | MEDIUM | HIGH — definido pelo /medical-gate
gate_i_aprovado: false   # true após aprovação HITL dos constraints
gate_ii_aprovado: false  # true após aprovação de profissional de saúde
---

# Spec: [Nome da Feature]

**Projeto**: Vitalia Kit v2
**Data**: DD-MM-YYYY HH:MM:SS(GMT-04:00)
**Autor**: [nome]
**Status**: DRAFT

---

## Visão Geral

> Uma frase descrevendo o que esta feature faz e para quem.

---

## Requisitos Funcionais

- RF-01: [descrição]
- RF-02: [descrição]

## Requisitos Não-Funcionais

- RNF-01: [desempenho, segurança, privacidade, etc.]

## Histórias de Usuário

```
Como [tipo de usuário],
quero [ação ou funcionalidade],
para que [benefício ou objetivo].
```

## Critérios de Aceite

- [ ] [critério verificável 1]
- [ ] [critério verificável 2]

## Escopo Negativo (Fora do Escopo)

- [o que esta spec explicitamente NÃO cobre]

---

## Medical Constraints

> Definidos pelo `/medical-gate` em: DD-MM-YYYY HH:MM:SS(GMT-04:00)
> Nível de risco: [MEDIUM | HIGH]
> Gate I aprovado por: [usuário] em DD-MM-YYYY HH:MM:SS(GMT-04:00)

| ID | Constraint | Evidência | Nível |
|---|---|---|---|
| MC-GLOBAL-001 | FC Máxima = 208 − 0,7 × idade (Tanaka) | Tanaka et al., 2001 — JACC | A |
| MC-NNN | [descrição do constraint específico] | [fonte] | [A/B/C] |

### Restrições de Publicação (Gate II)

- [ ] Disclaimer educacional presente em toda exibição ao usuário
- [ ] Aprovação de profissional de saúde: [nome] — [especialidade] — DD-MM-YYYY
- [ ] Conteúdo não faz promessa terapêutica ou diagnóstica

---

## Notas de Implementação

> Contexto técnico relevante para o `/spec-plan`. Não é código — é orientação.

- [nota 1]
- [nota 2]
