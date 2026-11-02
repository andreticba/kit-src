<!-- ADR-001-handoff-local-desacoplado-redis.md | Vitalia SDD v0.6.0 | 17-10-2026 06:45(GMT-04:00) -->
# ADR-001: Desacoplamento do Redis e Adoção do Ledger Local de Handoffs

- **Status:** APPROVED
- **Data:** 17-10-2026 06:45(GMT-04:00)
- **Autor:** Vitalia Tech Lead / SDD Core Team
- **Princípios Constitucionais:** P00, P01, P04, P11, P12

## Contexto
O ecossistema Vitalia contava com referências a filas de mensagens e streams Redis (`vitalia:handoffs`, `vitalia:events`) que dependiam da existência de daemons externos ativos. Durante auditoria técnica (achado A4 de `kit_routing_audit.md`), identificou-se que essa dependência impunha sobrecarga operacional e falhas silenciosas quando executado em ambientes locais ou sem serviços de infraestrutura iniciados.

## Opções Consideradas
1. **Obrigatoriedade de container Redis local:** Exigir `redis-server` rodando em segundo plano. Descartado por violar o princípio de operação zero-dependency e adicionar atrito à DX.
2. **Ledger Local de Handoffs em Arquivos JSON:** Utilizar o sistema de arquivos local com serialização JSON e validação estrita via schema formal.
3. **SQLite Embutido:** Criar banco SQLite local para handoffs. Descartado por complexidade desnecessária de concorrência frente ao modelo de despacho atômico de arquivos únicos.

## Decisão
Adotar a Opção 2: Desacoplar temporariamente o Redis e implementar o módulo utilitário `vitalia_handoff.py` operando sobre o diretório de dados local do projeto (`.vitalia/memory/data_storage/handoffs/`), garantindo execução 100% determinística, local e resiliente sem dependência de daemons de terceiros.

## Consequências
- **Positivas:** Operação imediata em qualquer ambiente de desenvolvimento (Linux/macOS), eliminação de falsas asserções de telemetria Redis, latência de criação de handoff inferior a 10ms.
- **Trade-offs:** Handoffs são consumidos via filesystem do repositório local; suporte a mensageria distribuída multi-máquina permanece postergado para ciclos futuros de alta escala.
