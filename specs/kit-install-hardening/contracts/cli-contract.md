<!-- cli-contract.md | Vitalia SDD v0.6.0 | 31-10-2026 15:50:00(GMT-04:00) -->
> **cli-contract.md | Vitalia SDD v0.6.0 | 31-10-2026 15:50:00(GMT-04:00)**

# CLI Contract: vitalia_handoff.py --project-root

## Visão Geral

O argumento `--project-root` é adicionado a todos os subcomandos do CLI para permitir execução determinística independente do `cwd`.

## Subcomandos Afetados

### `create --project-root PATH`

```
python3 ~/.vitalia/src/vitalia_handoff.py create \
    --project-root /caminho/para/projeto \
    --source "workflow-a" \
    --target "workflow-b" \
    --intent "intent_type" \
    --input "user input" \
    --summary "resumo"
```

**Comportamento:**
- Usa `PATH` como raiz do projeto (pula `resolve_project_root`).
- Valida que `PATH/.vitalia/memory/data_storage` existe.
- Guardrail: rejeita se `PATH` estiver sob `~/.vitalia`.
- Cria `handoffs/` se necessário.

**Exit codes:**
- `0`: handoff criado com sucesso.
- `1`: erro (projeto inválido, guardrail, sem data_storage).

### `latest --project-root PATH`

```
python3 ~/.vitalia/src/vitalia_handoff.py latest \
    --project-root /caminho/para/projeto \
    --target "workflow-b"
```

**Comportamento:**
- Busca o handoff pendente mais recente no projeto informado.
- Se `--project-root` não informado, usa `resolve_project_root(cwd)`.

**Exit codes:**
- `0`: caminho do handoff impresso em stdout (ou vazio se nenhum pendente).
- `1`: erro.

### `consume --project-root PATH --file FILEPATH`

```
python3 ~/.vitalia/src/vitalia_handoff.py consume \
    --project-root /caminho/para/projeto \
    --file "caminho/relativo/ou/absoluto.json"
```

**Comportamento:**
- `--project-root` é informativo (para contexto); o `--file` é o caminho direto do handoff.
- Marca o handoff como `consumed`.

### `validate --project-root PATH --file FILEPATH`

**Comportamento idêntico ao `consume`**, mas sem alterar o status.

## Comportamento Sem `--project-root`

Quando `--project-root` é omitido, o CLI chama `resolve_project_root(start=Path.cwd())` para detectar automaticamente o projeto. As regras de resolução estão documentadas na spec FR-001.
