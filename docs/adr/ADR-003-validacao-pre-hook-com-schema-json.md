<!-- ADR-003-validacao-pre-hook-com-schema-json.md | Vitalia SDD v0.6.0 | 17-10-2026 06:45(GMT-04:00) -->
# ADR-003: Validação Pré-Hook Obrigatória contra Schema Formal (`vitalia-handoff-v1.0.0.json`)

- **Status:** APPROVED
- **Data:** 17-10-2026 06:45(GMT-04:00)
- **Autor:** Vitalia Tech Lead / SDD Core Team
- **Princípios Constitucionais:** P01, P02, P04, P12, P14

## Contexto
A transferência de contexto inter-agentes ocorria sem contratos estritos, permitindo que payloads parciais, malformados ou corrompidos por alucinação chegassem à janela de contexto de workflows e modelos LLM, provocando falhas catastróficas em tempo de execução.

## Opções Consideradas
1. **Tipagem Flexível com Dicionários Python:** Validação heurística de chaves por código procedural ad-hoc. Descartado por fragilidade e falta de conformidade formal.
2. **Validação Estrita via JSON Schema Draft-07:** Formalização do contrato canônico [`vitalia-handoff-v1.0.0.json`](file:///home/andre/projetos/assistidos/kit_src/source/src/schemas/vitalia-handoff-v1.0.0.json) e validação obrigatória no pré-hook do Guardian com biblioteca `jsonschema`.
3. **Pydantic Models Runtime:** Utilizar schemas Pydantic v2. Descartado para manter dependências mínimas no kit padrão e interoperabilidade universal com JSON standard.

## Decisão
Adotar a Opção 2: Validação obrigatória e fail-fast com `jsonschema.validate()` antes de qualquer ingestão de handoff no Guardian (`session_context.handoff`). Se inválido, o processo é abortado imediatamente com código de erro 1.

## Consequências
- **Positivas:** Prevenção contra injeção de contexto corrompido, alucinação de envelopes, conformidade com OWASP LLM01/07 e princípio P12. Latência comprovada < 100ms (p95).
- **Trade-offs:** Exige estrita adesão ao schema e versionamento explícito de campos ao evoluir o contrato.
