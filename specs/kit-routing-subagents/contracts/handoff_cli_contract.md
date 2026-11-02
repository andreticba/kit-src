<!-- handoff_cli_contract.md | Vitalia SDD v0.6.0 | 18-10-2026 00:41(GMT-04:00) -->
# Interface Contract: Módulo Utilitário e CLI `vitalia_handoff.py`

Este documento formaliza as assinaturas da biblioteca Python e da interface de linha de comando (CLI) do utilitário `source/src/vitalia_handoff.py`.

---

## 1. Interface Python (Biblioteca)

```python
from pathlib import Path
from typing import Dict, Any, Optional

def create_handoff(
    source_workflow: str,
    target_workflow: str,
    intent_type: str,
    source_input: str,
    normalized_summary: str,
    detected_domain: str,
    feature_context: str,
    direction: str = "forward",  # "forward" | "reverse" | "fallback"
    confidence: float = 1.0,
    ttl_seconds: int = 3600,
    project_root: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Gera programmaticamente um payload completo de handoff, salva em 
    .vitalia/memory/data_storage/handoffs/handoff_<source>_to_<target>_<uuid_8>.json
    e retorna o dict gerado.
    
    Regras de Nomenclatura:
        Arquivo físico nomeado canonicamente como:
        handoff_{source_workflow}_to_{target_workflow}_{uuid[:8]}.json
    
    Regras de Direção:
        direction deve ser 'forward' (padrão / entrada de usuário / avanço),
        'reverse' (retorno de especialista com JSON de contexto ou escalação invertida)
        ou 'fallback' (quando o roteador devolve para ideação socrática).
        
    Raises:
        jsonschema.ValidationError: se o payload gerado violar vitalia-handoff-v1.0.0.json.
        OSError: se a escrita no disco falhar.
    """
    ...

def validate_handoff_file(file_path: Path) -> Dict[str, Any]:
    """
    Lê e valida estruturalmente o arquivo JSON contra o schema oficial 
    source/src/schemas/vitalia-handoff-v1.0.0.json.
    
    Retorna o payload validado ou levanta jsonschema.ValidationError.
    """
    ...

def consume_handoff(file_path: Path) -> Dict[str, Any]:
    """
    Realiza a mutação atômica do campo envelope.status para 'consumed' 
    utilizando escrita temporária + os.replace.
    """
    ...

def get_latest_pending_handoff(project_root: Optional[Path] = None) -> Optional[Path]:
    """
    Localiza o handoff pendente mais recente no diretório data_storage/handoffs/
    que ainda esteja dentro do período de TTL.
    """
    ...
```

---

## 2. Interface CLI (Linha de Comando)

### Comando: `create`
```bash
python3 source/src/vitalia_handoff.py create \
    --source "brainstorming" \
    --target "vitalia-route" \
    --direction "forward" \
    --intent "brainstorming_to_route" \
    --input "Refatorar roteamento" \
    --summary "specs/kit-routing-subagents/research-brainstorming.md" \
    --domain "engenharia_software" \
    --feature "specs/kit-routing-subagents" \
    --confidence 0.95
```
- **Saída stdout**: JSON com o caminho do arquivo gerado (`handoff_brainstorming_to_vitalia-route_<uuid_8>.json`) e `handoff_id`.

### Comando: `validate`
```bash
python3 source/src/vitalia_handoff.py validate --file ".vitalia/memory/data_storage/handoffs/handoff_brainstorming_to_vitalia-route_<uuid_8>.json"
```
- **Saída**: Exit code 0 se válido; Exit code 1 com descrição do erro no stderr se inválido.

### Comando: `consume`
```bash
python3 source/src/vitalia_handoff.py consume --file ".vitalia/memory/data_storage/handoffs/handoff_brainstorming_to_vitalia-route_<uuid_8>.json"
```
- **Saída**: Exit code 0 após atualização atômica de status para `"consumed"`.

### Comando: `latest`
```bash
python3 source/src/vitalia_handoff.py latest
```
- **Saída stdout**: Caminho absoluto do último arquivo pendente válido ou vazio se nenhum existir.
