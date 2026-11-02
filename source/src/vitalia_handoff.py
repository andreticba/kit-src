# vitalia_handoff.py | Vitalia SDD v0.6.0 | 18-10-2026 11:25(GMT-04:00)
"""
Módulo de utilitários e CLI para criação, validação estrutural e consumo atômico
de handoffs inter-agente locais em .vitalia/memory/data_storage/handoffs/.
Contratos: C12, C14, handoff_cli_contract.md.
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional, Union
import uuid

import jsonschema

# Resolução de diretórios do Kit Global
CURRENT_DIR = Path(__file__).resolve().parent
DEFAULT_SCHEMA_PATH = CURRENT_DIR / "schemas" / "vitalia-handoff-v1.0.0.json"


def resolve_project_root(start: Optional[Union[str, Path]] = None) -> Path:
    """
    Resolve a raiz do projeto Vitalia a partir de 'start' (ou cwd).

    Regras (FR-001):
    1. Se start estiver dentro de uma árvore .vitalia/, sobe para fora dela.
    2. Sobe procurando .vitalia/ de projeto (contém feature.json, config.yml ou memory/).
    3. Ignora $HOME e o diretório do Kit Global (~/.vitalia ou VITALIA_KIT_DIR).
    4. Para ao alcançar $HOME ou a raiz do filesystem (/).

    Raises:
        RuntimeError com instrução para executar install-project.
    """
    curr = Path(start).resolve() if start is not None else Path.cwd().resolve()
    home = Path.home().resolve()
    kit_dir_env = os.environ.get("VITALIA_KIT_DIR")
    kit_dir = Path(kit_dir_env).resolve() if kit_dir_env else (home / ".vitalia")

    # 1. Se start estiver dentro de uma árvore .vitalia/, sobe para fora dela
    while curr.name == ".vitalia" or any(p.name == ".vitalia" for p in curr.parents):
        if curr == curr.parent:
            break
        curr = curr.parent

    # 2. Sobe procurando .vitalia/ de projeto
    while True:
        # 3 & 4. Ignora $HOME e VITALIA_KIT_DIR (~/.vitalia) e para ao alcançar $HOME
        if curr == home or curr == kit_dir:
            break

        dot_vitalia = curr / ".vitalia"
        if dot_vitalia.is_dir() and dot_vitalia.resolve() != kit_dir:
            is_project = (
                (dot_vitalia / "feature.json").exists()
                or (dot_vitalia / "config.yml").exists()
                or (dot_vitalia / "memory").exists()
            )
            if is_project:
                return curr

        parent = curr.parent
        if parent == curr:  # Raiz do filesystem
            break
        curr = parent

    raise RuntimeError(
        "Nenhum projeto Vitalia encontrado. Execute 'install-project' para inicializar o projeto."
    )


def resolve_storage_dir(
    start: Optional[Union[str, Path]] = None,
    lenient: bool = False
) -> Optional[Path]:
    """
    Resolve o diretório de storage de handoffs do projeto ativo.

    Regras (FR-002, FR-003, FR-005):
    1. Localiza a raiz via resolve_project_root(start). Se não encontrar:
       - Se lenient=True, retorna None silenciosamente.
       - Se lenient=False, propaga RuntimeError com instrução para install-project.
    2. Valida a existência de .vitalia/memory/data_storage:
       - Se ausente e lenient=True, retorna None.
       - Se ausente e lenient=False, lança RuntimeError com:
         "Execute novamente o install-project para inicializar data_storage e a conexão com o GitHub."
    3. Guardrail Zero Data Leak (FR-003):
       - Se a raiz for $HOME ou o caminho final estiver sob ~/.vitalia, emite erro fatal.
    4. Retorna <project_root>/.vitalia/memory/data_storage/handoffs (criando handoffs se necessário).
    """
    try:
        project_root = resolve_project_root(start)
    except RuntimeError:
        if lenient:
            return None
        raise

    home = Path.home().resolve()
    kit_dir_env = os.environ.get("VITALIA_KIT_DIR")
    kit_dir = Path(kit_dir_env).resolve() if kit_dir_env else (home / ".vitalia")

    # Guardrail Zero Data Leak: raiz nunca pode ser $HOME
    if project_root.resolve() == home:
        raise RuntimeError(
            "Violação Zero Data Leak: a raiz do projeto não pode ser o diretório $HOME."
        )

    data_storage = project_root / ".vitalia" / "memory" / "data_storage"
    if not data_storage.is_dir():
        if lenient:
            return None
        raise RuntimeError(
            "Execute novamente o install-project para inicializar data_storage e a conexão com o GitHub."
        )

    storage_dir = data_storage / "handoffs"
    resolved_storage = storage_dir.resolve()

    # Guardrail Zero Data Leak: caminho final não pode estar sob kit_dir (~/.vitalia)
    try:
        resolved_storage.relative_to(kit_dir)
        raise RuntimeError(
            "Violação Zero Data Leak: tentativa de acessar storage global em ~/.vitalia."
        )
    except ValueError:
        pass

    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def get_default_storage_dir(project_root: Optional[Union[str, Path]] = None) -> Path:
    """Retorna o diretório local isolado de persistência de handoffs."""
    if project_root:
        res = resolve_storage_dir(start=project_root, lenient=False)
        assert res is not None
        return res
    res = resolve_storage_dir(lenient=False)
    assert res is not None
    return res


def get_machine_id() -> str:
    """Gera identificador determinístico da máquina atual."""
    raw = os.environ.get("VITALIA_MACHINE_NAME") or os.uname().nodename
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]


def load_schema(schema_path: Optional[Path] = None) -> Dict[str, Any]:
    """Carrega o JSON Schema oficial de handoff."""
    path = schema_path or DEFAULT_SCHEMA_PATH
    if not path.exists():
        raise FileNotFoundError(f"Schema de handoff não encontrado em: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_handoff_filename(source_workflow: str, target_workflow: str, handoff_id: str) -> str:
    """Gera nome semântico canônico: handoff_<source>_to_<target>_<uuid_8>.json"""
    short_uuid = handoff_id.split("-")[0] if "-" in handoff_id else handoff_id[:8]
    return f"handoff_{source_workflow}_to_{target_workflow}_{short_uuid}.json"


class HandoffPath(type(Path())):
    """Path especializado que também carrega o payload no atributo payload."""
    payload: Dict[str, Any]


def create_handoff(
    source_workflow: str,
    target_workflow: str,
    intent_type: str,
    source_input: str,
    normalized_summary: str,
    direction: str = "forward",
    detected_domain: str = "",
    feature_context: str = "",
    confidence: float = 1.0,
    ttl_seconds: int = 3600,
    project_root: Optional[Path] = None,
    storage_dir: Optional[Path] = None,
    suggested_command: str = "",
    match_level: str = "semantic",
    match_source: str = "",
    pipeline_stage: str = "brainstorming"
) -> Path:
    """
    Gera programmaticamente um payload completo de handoff, salva em
    .vitalia/memory/data_storage/handoffs/handoff_<source>_to_<target>_<uuid_8>.json
    com atomicidade e retorna o Path do arquivo gerado.
    """
    if direction not in ("forward", "reverse", "fallback"):
        raise ValueError(f"direction inválida: {direction}. Esperado: forward, reverse ou fallback.")

    handoff_id = str(uuid.uuid4())
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    machine_id = get_machine_id()

    payload: Dict[str, Any] = {
        "$schema": "vitalia-handoff-v1.0.0",
        "schema_type": "workflow_handoff",
        "schema_version": "1.0.0",
        "envelope": {
            "handoff_id": handoff_id,
            "created_at": now_iso,
            "ttl_seconds": ttl_seconds,
            "source_workflow": source_workflow,
            "target_workflow": target_workflow,
            "direction": direction,
            "machine_id": machine_id,
            "status": "pending"
        },
        "intent": {
            "intent_type": intent_type,
            "source_input": source_input,
            "normalized_summary": normalized_summary[:120],
            "confidence": float(confidence),
            "match_level": match_level,
            "match_source": match_source or f"routing_table.{source_workflow}",
            "target_command": suggested_command or f"/{target_workflow}",
            "detected_domain": detected_domain,
            "pipeline_stage": pipeline_stage,
            "feature_context": feature_context
        },
        "session_snapshot": {
            "active_feature": feature_context,
            "p0": "Transição de contexto determinística local",
            "machine_id": machine_id,
            "env_summary": {
                "python": sys.version.split()[0]
            }
        },
        "routing": {
            "confirmed_by_user": True,
            "confirmation_timestamp": now_iso,
            "suggested_command": suggested_command or f"/{target_workflow}",
            "fallback_used": (direction == "fallback")
        }
    }

    # Valida contra o schema antes de gravar
    schema = load_schema()
    jsonschema.validate(instance=payload, schema=schema)

    # Persistência atômica
    target_dir = storage_dir or get_default_storage_dir(project_root)
    filename = generate_handoff_filename(source_workflow, target_workflow, handoff_id)
    final_path = target_dir / filename
    tmp_path = target_dir / f".{filename}.tmp"

    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    os.replace(tmp_path, final_path)
    return final_path


def validate_handoff_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Lê e valida estruturalmente o arquivo JSON contra o schema oficial."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo de handoff inexistente: {path}")

    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    schema = load_schema()
    jsonschema.validate(instance=payload, schema=schema)
    return payload


def validate_handoff(target: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
    """Alias flexível para validação de arquivo ou dict em memória."""
    if isinstance(target, dict):
        schema = load_schema()
        jsonschema.validate(instance=target, schema=schema)
        return target
    return validate_handoff_file(Path(target))


def consume_handoff(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Realiza a mutação atômica do campo envelope.status para 'consumed'."""
    path = Path(file_path)
    payload = validate_handoff_file(path)

    payload["envelope"]["status"] = "consumed"
    schema = load_schema()
    jsonschema.validate(instance=payload, schema=schema)

    tmp_path = path.parent / f".{path.name}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    os.replace(tmp_path, path)
    return payload


def get_latest_pending_handoff(
    project_root: Optional[Path] = None,
    target_workflow: Optional[str] = None,
    storage_dir: Optional[Path] = None
) -> Optional[Path]:
    """Localiza o handoff pendente mais recente não expirado."""
    target_dir = storage_dir or get_default_storage_dir(project_root)
    if not target_dir.exists():
        return None

    candidates = []
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    for json_file in target_dir.glob("handoff_*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            envelope = data.get("envelope", {})
            if envelope.get("status") != "pending":
                continue

            if target_workflow:
                t_clean = target_workflow.removeprefix("vitalia-")
                e_clean = str(envelope.get("target_workflow", "")).removeprefix("vitalia-")
                if t_clean != e_clean:
                    continue

            created_str = envelope.get("created_at")
            ttl = envelope.get("ttl_seconds", 3600)
            if created_str:
                # Trata timezone Z
                clean_str = created_str.replace("Z", "+00:00")
                created_dt = datetime.datetime.fromisoformat(clean_str)
                age = (now_utc - created_dt).total_seconds()
                if age > ttl:
                    continue
                candidates.append((created_dt, json_file))
        except Exception:
            continue

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def latest_handoff(
    target_workflow: Optional[str] = None,
    storage_dir: Optional[Path] = None,
    project_root: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """Recupera o dict do handoff pendente mais recente."""
    path = get_latest_pending_handoff(
        project_root=project_root,
        target_workflow=target_workflow,
        storage_dir=storage_dir
    )
    if not path:
        return None
    return validate_handoff_file(path)


def main():
    parser = argparse.ArgumentParser(description="Vitalia Handoff CLI Utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcomando create
    parser_create = subparsers.add_parser("create", help="Cria um novo handoff atômico")
    parser_create.add_argument("--project-root", default=None, help="Raiz do projeto Vitalia")
    parser_create.add_argument("--source", required=True, help="Workflow de origem")
    parser_create.add_argument("--target", required=True, help="Workflow de destino")
    parser_create.add_argument("--intent", required=True, help="Tipo de intenção")
    parser_create.add_argument("--input", required=True, help="Input de origem do usuário")
    parser_create.add_argument("--summary", required=True, help="Resumo normalizado ou caminho de contexto")
    parser_create.add_argument("--direction", default="forward", choices=["forward", "reverse", "fallback"], help="Direção do handoff")
    parser_create.add_argument("--domain", default="", help="Domínio detectado")
    parser_create.add_argument("--feature", default="", help="Feature context")
    parser_create.add_argument("--confidence", type=float, default=1.0, help="Nível de confiança")
    parser_create.add_argument("--ttl", type=int, default=3600, help="TTL em segundos")

    # Subcomando validate
    parser_val = subparsers.add_parser("validate", help="Valida um arquivo de handoff")
    parser_val.add_argument("--project-root", default=None, help="Raiz do projeto Vitalia")
    parser_val.add_argument("--file", required=True, help="Caminho do arquivo JSON")

    # Subcomando consume
    parser_con = subparsers.add_parser("consume", help="Consome um arquivo de handoff marcando como consumed")
    parser_con.add_argument("--project-root", default=None, help="Raiz do projeto Vitalia")
    parser_con.add_argument("--file", required=True, help="Caminho do arquivo JSON")

    # Subcomando latest
    parser_lat = subparsers.add_parser("latest", help="Obtém o último handoff pendente")
    parser_lat.add_argument("--project-root", default=None, help="Raiz do projeto Vitalia")
    parser_lat.add_argument("--target", default=None, help="Filtrar por target workflow")

    args = parser.parse_args()

    try:
        p_root = Path(args.project_root) if getattr(args, "project_root", None) else None

        if args.command == "create":
            path = create_handoff(
                source_workflow=args.source,
                target_workflow=args.target,
                intent_type=args.intent,
                source_input=args.input,
                normalized_summary=args.summary,
                direction=args.direction,
                detected_domain=args.domain,
                feature_context=args.feature,
                confidence=args.confidence,
                ttl_seconds=args.ttl,
                project_root=p_root
            )
            payload = validate_handoff_file(path)
            print(json.dumps({
                "status": "created",
                "file": str(path.resolve()),
                "handoff_id": payload["envelope"]["handoff_id"],
                "direction": payload["envelope"]["direction"]
            }, indent=2))
            sys.exit(0)

        elif args.command == "validate":
            payload = validate_handoff_file(Path(args.file))
            print(json.dumps({"status": "valid", "handoff_id": payload["envelope"]["handoff_id"]}, indent=2))
            sys.exit(0)

        elif args.command == "consume":
            payload = consume_handoff(Path(args.file))
            print(json.dumps({"status": "consumed", "handoff_id": payload["envelope"]["handoff_id"]}, indent=2))
            sys.exit(0)

        elif args.command == "latest":
            latest_path = get_latest_pending_handoff(
                target_workflow=args.target,
                project_root=p_root
            )
            if latest_path:
                print(str(latest_path.resolve()))
                sys.exit(0)
            else:
                sys.exit(0)

    except Exception as e:
        sys.stderr.write(f"Erro em vitalia_handoff ({args.command}): {str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
