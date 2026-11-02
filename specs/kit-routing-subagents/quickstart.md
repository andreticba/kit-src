<!-- quickstart.md | Vitalia SDD v0.6.0 | 17-10-2026 10:28(GMT-04:00) -->
# Quickstart & Verification Guide: kit-routing-subagents

Este guia apresenta o roteiro prático e reprodutível de validação ponta a ponta da arquitetura de roteamento e handoff local.

---

## Cenário 1: Validação do Ciclo de Handoff Local (Brainstorming ➔ Route)

### 1. Criar um handoff sintético simulando a saída do Brainstorming:
```bash
python3 source/src/vitalia_handoff.py create \
    --source "brainstorming" \
    --target "vitalia-route" \
    --intent "brainstorming_to_route" \
    --input "Refatoração de Roteamento" \
    --summary "specs/kit-routing-subagents/research-brainstorming.md" \
    --domain "engenharia_software" \
    --feature "specs/kit-routing-subagents" \
    --confidence 0.98
```
- **Resultado Esperado:** Arquivo criado em `.vitalia/memory/data_storage/handoffs/handoff_<uuid>.json` com status `"pending"`.

### 2. Validar o arquivo gerado contra o Schema Formal:
```bash
HANDOFF_FILE=$(python3 source/src/vitalia_handoff.py latest)
python3 source/src/vitalia_handoff.py validate --file "$HANDOFF_FILE"
```
- **Resultado Esperado:** Exit code 0, nenhuma mensagem de erro.

### 3. Consumir o Handoff simulando o despacho:
```bash
python3 source/src/vitalia_handoff.py consume --file "$HANDOFF_FILE"
cat "$HANDOFF_FILE" | grep '"status": "consumed"'
```
- **Resultado Esperado:** O campo `envelope.status` foi alterado atomicamente para `"consumed"`.

---

## Cenário 2: Validação de Idempotência no Instalador (`install-project`)

### 1. Executar o instalador do projeto:
```bash
./source/bin/install-project
```

### 2. Verificar a nomenclatura canônica dos atalhos de skill:
```bash
ls -d .agents/skills/vitalia-*
```
- **Resultado Esperado:**
  - Existe `.agents/skills/vitalia-route/`
  - Existe `.agents/skills/vitalia-integrative-review/`
  - **NÃO** existe nenhum diretório duplicado do tipo `.agents/skills/vitalia-vitalia-*`.

---

## Cenário 3: Validação do Catálogo de Agentes e Status Operacional

### 1. Inspecionar o catálogo processado pelo Guardian:
```bash
python3 -c '
import yaml
with open("source/profiles/agents_catalog.yaml") as f:
    data = yaml.safe_load(f)
planned = [a["name"] for a in data["agents"] if a.get("status") == "planned"]
active = [a["name"] for a in data["agents"] if a.get("status") == "active"]
print(f"Ativos: {len(active)} | Planejados: {len(planned)}")
assert "django-stark" in planned
assert "master-ai-control" in planned
print("Catálogo validado com sucesso!")
'
```
- **Resultado Esperado:** Agentes do AI-Control presentes com status `"planned"`.
