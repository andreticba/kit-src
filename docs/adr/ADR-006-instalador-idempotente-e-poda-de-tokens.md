<!-- ADR-006-instalador-idempotente-e-poda-de-tokens.md | Vitalia SDD v0.6.0 | 17-10-2026 10:15(GMT-04:00) -->
# ADR-006: Nomenclatura Idempotente no Instalador (`install-project`) e Equalização de Tokens no Guardian por Perfil de Hardware

- **Status:** APPROVED
- **Data:** 17-10-2026 10:15(GMT-04:00)
- **Autor:** Vitalia Tech Lead / SDD Core Team
- **Princípios Constitucionais:** P00, P01, P02, P04, P11, P16

## Contexto
Durante a auditoria técnica do sistema de roteamento (`kit_routing_audit.md`), dois problemas críticos de infraestrutura e gestão de contexto foram identificados:
1. **Duplicação de Prefixos no Instalador (Achado A3):** No script `source/bin/install-project`, extensões cujos nomes já continham o prefixo `vitalia-` (ex: `vitalia-route.toml`, `vitalia-integrative-review.toml`) geravam diretórios com duplicação espúria (`.agents/skills/vitalia-vitalia-route/`).
2. **Ausência de Aplicação das Cotas nos Adaptadores (Achado A10):** O `GuardianContextV2` possui um subsistema nativo de equalização proporcional de contexto (`total_budget` e `source_weights`), calculando a cota individual `src_token_limit = int(total_budget * src_weight)`. Contudo, os adaptadores (`RoutingTableAdapter`, `AgentsCatalogAdapter`, `BrainstormingIntentsAdapter`) ignoravam o parâmetro `token_limit` e devolviam os YAMLs inteiros sem podar. Isso gerava injeções de mais de 4000 tokens, sobrecarregando LLMs locais (como o Qwen2.5 3B no Ollama durante a execução de gates constitucionais) e introduzindo ruído cognitivo até mesmo em modelos de fronteira na IDE.

## Opções Consideradas

### Para Nomenclatura no Instalador:
1. **Renomear arquivos TOML originais:** Descartado por quebrar compatibilidade retroativa.
2. **Normalização Heurística Idempotente com sed:** Aplicar expressão regular determinística `clean_name=$(echo "${ext_name}" | sed 's/^vitalia-//')` gerando invariavelmente `skill_name="vitalia-${clean_name}"`.

### Para Gestão e Equalização de Tokens:
1. **Limite Estático e Rígido Universal:** Forçar um corte fixo de tokens (ex: 1000 tokens) para todos os fluxos. Descartado por subutilizar desnecessariamente as janelas de contexto de modelos de fronteira na IDE (Claude 3.5 Sonnet, Gemini Pro).
2. **Poda Cega por Truncamento de Caracteres:** Truncar strings brutas. Descartado por corromper a sintaxe de estruturas JSON/YAML (violação do Princípio P16).
3. **Equalização Polimórfica Sensível ao `hardware_profile` com Poda Semântica (Escolhida):** Utilizar o mecanismo nativo de cotas calibradas (`total_budget` + `source_weights`) do `GuardianContextV2`, diferenciando o teto global pelo perfil de hardware declarado:
   - **Perfil `frontier` (IDE / Modelos de Fronteira):** Orçamento expandido de até 4.000 tokens, provendo visão abrangente de agentes e capacidades sem ruído excessivo.
   - **Perfil `lightweight` / `local` (Gates Constitucionais / Ollama local):** Orçamento restrito de até 1.000 tokens, prevenindo estouro de contexto e alucinações cognitivas em hardware modesto (GTX 1060 6GB / CPU).
   - **Poda Semântica:** Os adaptadores filtram prioritariamente entidades com `status: "planned"` e mantêm rotas estritamente relevantes ao contexto ativo (`feature_context`), preservando a validade estrutural dos dados.

## Decisão
1. Adotar a normalização determinística no script `source/bin/install-project` para garantir diretórios de skill canônicos e idempotentes em `.agents/skills/`.
2. Habilitar a equalização nativa do `GuardianContextV2` nos adaptadores (`RoutingTableAdapter`, `AgentsCatalogAdapter`, `BrainstormingIntentsAdapter`), respeitando a cota calculada `src_token_limit` e aplicando poda semântica sensível ao `hardware_profile` (`frontier` vs `lightweight`).

## Consequências
- **Positivas:**
  - Nomes de comandos perfeitamente canônicos em `.agents/skills/` (ex: `/vitalia-route` e `/vitalia-integrative-review`).
  - Proteção total do runtime local e gates constitucionais (SDDJudge) contra exaustão de contexto e alucinação.
  - Aproveitamento inteligente da capacidade da IDE com modelos de fronteira sem degradação por poluição de contexto.
  - Plena conformidade com os princípios constitucionais P11 (*Hardware-Agnostic Routing*) e P16 (*Artifact Integrity*).
- **Trade-offs:**
  - Exige que cada adaptador implemente a ordenação e descarte ordenado de itens em conformidade com sua cota proporcional.
