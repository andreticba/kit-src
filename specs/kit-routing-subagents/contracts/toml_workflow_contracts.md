<!-- toml_workflow_contracts.md | Vitalia SDD v0.6.0 | 17-10-2026 11:35(GMT-04:00) -->
# Contrato de Especificação e Semântica de Workflows TOML

**Data:** 17-10-2026 11:35(GMT-04:00)  
**Feature:** `kit-routing-subagents`  
**Escopo:** Mapeamento integral da arquitetura, semântica de seções, ciclo de interpolações e regras de edição cirúrgica para arquivos `.toml` em `source/extensions/`.

---

## 1. Arquitetura e Ciclo de Vida do TOML no Vitalia Kit

Os arquivos `.toml` em `source/extensions/*.toml` (espelhados em `~/.vitalia/extensions/`) não são meros arquivos de configuração; eles são **manifestos declarativos de workflows** que alimentam três camadas do ecossistema:

```
                  ┌────────────────────────────────────────┐
                  │        source/extensions/*.toml        │
                  └───────────────────┬────────────────────┘
                                      │
              ┌───────────────────────┼────────────────────────┐
              ▼                       ▼                        ▼
     [Instalador IDE]        [Hook Runner Runtime]       [Motor Guardian]
  source/bin/install-project  vitalia_hook_runner.py    guardian_context.py
              │                       │                        │
     Gera .agents/skills/     Executa [hooks] e      Poda YAMLs e injeta
       vitalia-*/SKILL.md    injeta Context Lifting    guardian_json
```

---

## 2. Especificação Canônica das Seções do TOML

### 2.1. Cabeçalho e Metadados Globais (Nível Raiz)

| Campo | Tipo | Obrigatoriedade | Semântica e Impacto no Sistema |
|---|---|---|---|
| Comentário de Abertura | `# ...` | Obrigatório | Carimbo temporal imutável `DD-MM-YYYY HH:MM(GMT-04:00)`, contratos SDD atendidos (ex: `C1, C2`) e papel do workflow. |
| `description` | `string` | Obrigatório | Resumo em linha única da missão do workflow. **Impacto Crítico:** O instalador `install-project` extrai este campo via regex para preencher o frontmatter YAML `description:` da `SKILL.md`. Não pode conter quebras de linha nem aspas duplas internas. |

### 2.2. Seção `[meta]`

```toml
[meta]
version = "0.6.0"
hardware_profile = "frontier" # ou "lightweight"
domain_gates = []
model_profile = "flash"       # opcional: "flash" ou "pro"
```

- **`version`**: Versão semântica do contrato do workflow.
- **`hardware_profile`**: Perfil de recursos. `frontier` indica que o workflow consome contexto estendido na IDE (orçamento até 4000 tokens no Guardian); `lightweight` impõe poda agressiva (até 1000 tokens) para inferência local no Ollama Qwen2.5 3B.
- **`model_profile`**: Quando presente, o `vitalia_hook_runner.py` ajusta a variável de ambiente `GEMINI_MODEL` no subprocesso (`pro` -> `gemini-3.1-pro-preview`, `flash` -> `gemini-3.6-flash`), isolando race conditions em execuções concorrentes.

### 2.3. Seção `[hooks]` e Resolução de Interpolações

```toml
[hooks]
before = ["python3 {{VITALIA_KIT_DIR}}/src/hooks/scan_environment.py"]
after  = []
```

- Executa comandos locais de pré/pós-condição. Se um hook falhar com exit code $\ne 0$, o runner aborta imediatamente com `status: "error"` (Trava STOP).
- **Interpolações Nativas suportadas por `resolve_placeholders()`:**
  - `{{cwd}}`: Diretório atual do workspace do projeto.
  - `{{VITALIA_KIT_DIR}}`: Caminho absoluto do kit (`~/.vitalia` ou `VITALIA_KIT_DIR`).
  - `{{FEATURE_DIR}}`: Diretório da feature ativa lido de `.vitalia/feature.json`.

### 2.4. Seção `[tools]` e `[context]`

```toml
[tools]
required = ["read_file"]
optional = ["write_file"]

[context]
reads = ["session_context", "routing_table", "agents_catalog"]
writes = []
```

- Declara ferramentas e fontes contextuais requeridas para governança e auditoria de segurança (P12).

### 2.5. Seção `[transport]`

```toml
[transport]
preferred     = "redis"
redis_key     = "vitalia:workflow:route"
file_path     = ".vitalia/pipeline.json"
session_shard = true
```

- Define canais de telemetria e fallback local. No ciclo atual de desacoplamento temporário do Redis (ADR-001), o sistema utiliza fallback de arquivo local determinístico.

### 2.6. Seção `[guardian]` e `prompt`

No padrão v0.6.0 (Context Lifting), a seção `[guardian]` declara as fontes dinâmicas que o `guardian_context.py` deve podar e compilar:

```toml
[guardian]
yaml_sources = ["constitution", "routing_table", "agents_catalog"]
guardian_profile = "gp_vitalia-route"

prompt = """
## Identidade ...
"""
```

> [!IMPORTANT]
> **A Regra Anti-"Lost in the Middle":**
> Em workflows modernos com `[guardian]`, o prompt **NÃO DEVE** conter a interpolação `{{args}}` solta no texto. 
> O argumento fornecido pelo usuário na IDE (`--args "{{args}}"`) é capturado pelo `vitalia_hook_runner.py` e injetado estruturadamente em `guardian_json.session_context.user_input`.
> A IA lê este dado via ferramenta `view_file` no arquivo JSON físico gerado em `~/.vitalia/tmp/`.

---

## 3. Matriz de Alterações Cirúrgicas dos TOMLs na Feature `kit-routing-subagents`

### 3.1. `source/extensions/brainstorming.toml`
* **Papel**: Supervisor Socrático.
* **Semântica Atual**: Roteava diretamente para comandos sem passar pelo dispatcher oficial e sem persistência formal de síntese intermediária.
* **Alteração Exata Exigida**:
  1. Preservar intactas as seções `[meta]`, `[hooks]`, `[tools]`, `[context]`, `[transport]` e `[guardian]`.
  2. Na seção `## 📋 Finalização do Ciclo`, substituir a regra de encerramento por:
     - Gerar obrigatoriamente o artefato Markdown `research-brainstorming.md` no diretório da feature ativa (`specs/<feature>/`).
     - Exibir o arquivo para revisão e edição soberana do usuário (HITL).
     - Executar o utilitário `vitalia_handoff.py create --intent-type brainstorming_to_route --summary specs/<feature>/research-brainstorming.md` persistindo em `.vitalia/memory/data_storage/handoffs/`.
     - Exibir a instrução final única de despacho: `/vitalia-route --handoff=<handoff_id>`.

### 3.2. `source/extensions/vitalia-route.toml`
* **Papel**: Dispatcher Oficial do Ecossistema.
* **Semântica Atual**: O prompt alegava falsamente gravação em streams Redis inexistentes (`vitalia:handoffs`) e não possuía suporte a handoff de entrada.
* **Alteração Exata Exigida**:
  1. No prompt, erradicar qualquer declaração de escrita direta em Redis.
  2. Adicionar instrução para leitura de `guardian_json.session_context.handoff`:
     - Se `session_context.handoff` estiver presente e válido, consumir a intenção originária e o link de `research-brainstorming.md`.
     - Invocar `vitalia_handoff.py consume <handoff_id>` para atomicamente marcar o payload como consumido.
     - Propor o workflow SDD adequado (`/vitalia-spec-specify`) com base no contexto ingerido.
  3. Preservar o fallback de retorno ao Brainstorming (`route_to_brainstorming`).

### 3.3. `source/extensions/spec-implement.toml` e `source/extensions/pair.toml`
* **Papel**: Executores de Código do SDD e Pair Programming.
* **Semântica Atual**: Executam tarefas sem protocolo formal de contenção quando encontram extrapolação de domínio ou nova regra de negócio.
* **Alteração Exata Exigida**:
  1. Inserir a diretriz de **Escalação Invertida (Protocolo HITL - FR-007 / ADR-004)**:
     - Se durante a implementação ou pareamento for identificada necessidade de alteração de regra de negócio, desvio de arquitetura ou novo requisito ausente nos ADRs/spec:
     - **Interromper imediatamente** a alteração de arquivos;
     - Gerar payload de handoff em `.vitalia/memory/data_storage/handoffs/` com `intent_type: "route_to_brainstorming"`;
     - Orientar o desenvolvedor a repactuar a arquitetura via `/vitalia-route --handoff=<id>` ou `/vitalia-brainstorming --handoff=<id>`.

---

## 4. Checklist Defensivo para Edição de Qualquer Arquivo TOML

Antes de salvar qualquer modificação em um `.toml`:
- [ ] O arquivo parseia sem erros via `python3 -c "import tomllib; tomllib.load(open('arquivo.toml', 'rb'))"`?
- [ ] A linha `description = "..."` permaneceu na raiz, sem aspas escapadas incorretamente?
- [ ] As variáveis de template de hooks `{{VITALIA_KIT_DIR}}` e `{{FEATURE_DIR}}` foram preservadas?
- [ ] O bloco de prompt utiliza strings literais multi-linha `"""` e não colide com interpolações indevidas?
- [ ] Nenhuma credencial ou caminho absoluto fora das variáveis do kit foi inserido?
- [ ] O cabeçalho foi atualizado com a data no fuso imutável `GMT-04:00`?
