<!-- ADR-005-catalogo-com-status-operacional-active-planned.md | Vitalia SDD v0.6.0 | 17-10-2026 06:45(GMT-04:00) -->
# ADR-005: Saneamento do Catálogo com Status Operacional (`status: active | planned`) e Ingestão da Equipe AI-Control

- **Status:** APPROVED
- **Data:** 17-10-2026 06:45(GMT-04:00)
- **Autor:** Vitalia Tech Lead / SDD Core Team
- **Princípios Constitucionais:** P00, P01, P02, P04, P08, P11

## Contexto
O arquivo `source/profiles/agents_catalog.yaml` continha agentes declarados que não possuíam arquivos de extensão `.toml` executáveis (achados A5 e A6 de `kit_routing_audit.md`). Isso gerava comandos fantasmas e propostas de roteamento para recursos inexistentes na instalação. Paralelamente, os 6 especialistas da equipe AI-Control (`Master AI-Control`, `Django-Stark`, `React-Vinci`, `Infra-Nomad`, `Cortex-Analyst`, `Figma-Maestro`) precisam ser incorporados formalmente ao catálogo como roadmap.

## Opções Consideradas
1. **Remover todos os agentes sem implementação:** Descartado pois apagaria a visão conceitual e roadmap do ecossistema.
2. **Implementar todos os 10 agentes simultaneamente:** Descartado por violar o escopo do ciclo e a disciplina do SDD (necessidade de specs dedicadas).
3. **Adicionar o Campo `status: "active" | "planned"`:** Mapear rigorosamente a existência física de arquivos executáveis `.toml`. Somente agentes com `status: "active"` podem ser sugeridos para despacho imediato. Os 6 especialistas AI-Control e 4 legados entram com `status: "planned"`.

## Decisão
Adotar a Opção 3: Incorporar `status: "active"` para agentes executáveis existentes e `status: "planned"` para os especialistas do AI-Control e entidades conceituais, atualizando o schema de validação e os adaptadores do Guardian.

## Consequências
- **Positivas:** Transparência total sobre capacidades em produção vs itens de roadmap, imunidade contra falhas de despacho de agentes fantasmas, preparação da infraestrutura para receber os TOMLs do AI-Control em ciclo subsequente.
- **Trade-offs:** Exige que novos agentes implementem obrigatoriamente a extensão `.toml` antes de serem promovidos para `status: "active"`.
