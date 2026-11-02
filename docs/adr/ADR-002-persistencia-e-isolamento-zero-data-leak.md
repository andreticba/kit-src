<!-- ADR-002-persistencia-e-isolamento-zero-data-leak.md | Vitalia SDD v0.6.0 | 17-10-2026 06:45(GMT-04:00) -->
# ADR-002: Persistência Segura e Isolamento de Handoffs em `data_storage` (Zero Data Leak)

- **Status:** APPROVED
- **Data:** 17-10-2026 06:45(GMT-04:00)
- **Autor:** Vitalia Tech Lead / SDD Core Team
- **Princípios Constitucionais:** P00, P02, P04, P07, P12, P17

## Contexto
O ecossistema gravava artefatos temporários e de contexto em pastas globais como `~/.vitalia/tmp` ou no `/tmp` do sistema operacional. Isso criava risco iminente de contaminação cruzada de dados confidenciais entre múltiplos projetos mantidos no mesmo host, violando a diretriz de soberania local (LGPD Art. 11/48, Princípio P07).

## Opções Consideradas
1. **Diretório Global `~/.vitalia/tmp`:** Reutilizar repositório global do usuário. Rejeitado por expor segredos e códigos proprietários a processos de outros workspaces.
2. **Diretório do SO `/tmp`:** Sujeito a limpeza automática do sistema, permissões globais permissivas e concorrência imprevisível. Rejeitado.
3. **Diretório Local do Projeto em `.vitalia/memory/data_storage/handoffs/`:** Encapsular toda persistência de handoffs dentro do repositório local.

## Decisão
Adotar a Opção 3: Todos os payloads de handoff (`handoff_<uuid>.json`) devem ser gravados exclusivamente em `.vitalia/memory/data_storage/handoffs/`. Gravações fora desse perímetro são estritamente proibidas e barradas em tempo de execução.

## Consequências
- **Positivas:** Isolamento hermético de contexto (Zero Data Leak), conformidade com Privacy by Design (P07), facilidade de expurgo e auditoria do histórico de handoffs do projeto.
- **Trade-offs:** Exige que a raiz do projeto possua o diretório `.vitalia/memory/data_storage/handoffs/` devidamente provisionado na inicialização da feature.
