<!-- ADR-004-escalacao-invertida-e-soberania-hitl.md | Vitalia SDD v0.6.0 | 17-10-2026 06:45(GMT-04:00) -->
# ADR-004: Protocolo de Escalação Invertida com Soberania Humana Obrigatória (HITL)

- **Status:** APPROVED
- **Data:** 17-10-2026 06:45(GMT-04:00)
- **Autor:** Vitalia Tech Lead / SDD Core Team
- **Princípios Constitucionais:** P00, P01, P02, P04, P09, P17

## Contexto
Agentes de IA e especialistas de implementação (ex: `Django-Stark`, `React-Vinci`) operando no nível de tarefas podem encontrar solicitações ou requisitos emergentes que alteram decisões arquiteturais já consolidadas ou expandem o escopo do projeto de forma não controlada, gerando erosão arquitetural e dívida técnica silenciosa.

## Opções Consideradas
1. **Agentes Decidem e Atualizam Arquitetura Autonomamente:** Permitir que o agente de IA altere ADRs ou crie novas entidades sem aprovação do desenvolvedor humano. Rejeitado categoricamente (viola P00 e P01).
2. **Ignorar Solicitação e Continuar Implementação:** Falha na captura de necessidades legítimas do usuário. Rejeitado.
3. **Protocolo de Escalação Invertida com Soberania HITL:** O agente interrompe o trabalho, gera um handoff de escalação com `intent_type: "route_to_brainstorming"` e instrui o desenvolvedor a repactuar a decisão através de `/vitalia-route` e `/vitalia-adr`.

## Decisão
Adotar a Opção 3: Qualquer agente ou workflow de execução que detectar divergência de escopo ou modificação arquitetural deve paralisar a execução e devolver o controle ao humano soberano via handoff de escalação invertida.

## Consequências
- **Positivas:** Preservação estrita da integridade arquitetural do repositório, soberania total do desenvolvedor humano, rastreabilidade transparente de novas decisões via ADR formal.
- **Trade-offs:** Pausas conscientes no fluxo de codificação para alinhamento socrático quando ocorrem mudanças estruturais.
