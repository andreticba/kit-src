# Vitalia Kit — Adaptador AG2

Este arquivo instrui o agente AG2 (AutoGen 2) sobre como usar o Vitalia Kit
via a tool `load_dynamic_skill`.

## Como carregar um workflow

O kit está instalado em `~/.vitalia/extensions/`.
Use a tool `load_dynamic_skill` para carregar qualquer workflow:

```python
# O agente chama a tool assim:
load_dynamic_skill("spec-specify")  # carrega ~/.vitalia/extensions/spec-specify.toml

# O tool_worker retorna o campo `prompt` do .toml
# O agente então executa as instruções do prompt
```

## Workflows disponíveis e perfis de hardware

| Workflow | Arquivo | Hardware | Quando usar |
|---|---|---|---|
| `spec-specify` | spec-specify.toml | lightweight | Traduzir pedido em spec.md |
| `spec-plan` | spec-plan.toml | lightweight | Planejar arquitetura técnica |
| `spec-tasks` | spec-tasks.toml | lightweight | Gerar checklist de tarefas |
| `spec-implement` | spec-implement.toml | heavy | Executar tarefas (escreve código) |
| `clarify` | clarify.toml | lightweight | Resolver ambiguidades da spec |
| `analyze` | analyze.toml | lightweight | Validar consistência dos artefatos |
| `brainstorming` | brainstorming.toml | lightweight | Estruturar features complexas |
| `session-start` | session-start.toml | lightweight | Iniciar sessão de trabalho |
| `session-end` | session-end.toml | lightweight | Encerrar e fazer shard da sessão |
| `session-consolidate` | session-consolidate.toml | lightweight | Sincronizar multi-máquina |
| `medical-gate` | medical-gate.toml | heavy | Gate de segurança clínica |
| `science-review` | science-review.toml | heavy | Revisão científica |
| `review` | review.toml | lightweight | Revisão de código |
| `pair` | pair.toml | lightweight | Modo pair programming |
| `continue` | continue.toml | lightweight | Retomar implementação |
| `debug` | debug.toml | lightweight | Debugging sistemático |
| `release` | release.toml | lightweight | Release com SemVer |
| `adr` | adr.toml | lightweight | Architecture Decision Record |

## Ciclo SDD completo no AG2

```python
# Fluxo típico no RoundRobinGroupChat do agente-local:
# 1. Arquiteto recebe pedido do usuário
# 2. Arquiteto carrega spec-specify via load_dynamic_skill
load_dynamic_skill("spec-specify")
# → Executa o prompt, gera specs/NNN/spec.md e .vitalia/feature.json

# 3. HITL: desenvolvedor revisa spec.md (via telemetry_api.py?)
# 4. Arquiteto carrega spec-plan
load_dynamic_skill("spec-plan")
# → Gera plan.md

# 5. Arquiteto carrega spec-tasks
load_dynamic_skill("spec-tasks")
# → Gera tasks.md, aciona analyze automaticamente

# 6. HITL: aprovação do tasks.md
# 7. Engenheiro carrega spec-implement
load_dynamic_skill("spec-implement")
# → Executa T001→TN marcando [X], valida Acceptance Scenarios
```

## Atualização necessária em tools.py

O `load_dynamic_skill` atual busca em `.specify/skills/`. Para usar o Vitalia
Kit 0.3, atualizar o caminho:

```python
def load_dynamic_skill(skill_name: str) -> str:
    """Carrega um workflow Vitalia Kit (.toml) para o contexto do agente."""
    kit_dir = os.path.expanduser("~/.vitalia/extensions")
    skill_path = os.path.join(kit_dir, f"{skill_name}.toml")
    try:
        import tomllib  # Python 3.11+
        with open(skill_path, "rb") as f:
            data = tomllib.load(f)
            return data.get("prompt", f"Erro: campo 'prompt' ausente em {skill_name}.toml")
    except FileNotFoundError:
        return f"Erro: Skill {skill_name} não encontrada em {kit_dir}."
    except Exception as e:
        return f"Erro ao carregar {skill_name}: {str(e)}"
```

## Detecção de Redis

O Kit detecta Redis via `.vitalia/config.yml` do projeto.
Se `redis_enabled: true`, o estado do workflow é transportado via Redis
usando a key definida em `[transport].redis_key` do `.toml` da extensão.
