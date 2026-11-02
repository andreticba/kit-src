# test_vitalia_handoff.py | Vitalia SDD v0.6.0 | 18-10-2026 11:20(GMT-04:00)
"""
Testes unitários para o módulo vitalia_handoff.py e conformidade com o schema
vitalia-handoff-v1.0.0.json (campo direction, persistência atômica, CLI e latência).
"""

import json
import os
import sys
import time
import pytest
from pathlib import Path
import jsonschema

# Assegura que o módulo source/src esteja no path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = REPO_ROOT / "source" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

SCHEMA_PATH = SRC_DIR / "schemas" / "vitalia-handoff-v1.0.0.json"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "handoff_valid.json"


@pytest.fixture
def handoff_schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def valid_handoff_payload():
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_schema_validates_canonical_payload(handoff_schema, valid_handoff_payload):
    """Garante que o payload válido com direction=forward é validado com sucesso."""
    jsonschema.validate(instance=valid_handoff_payload, schema=handoff_schema)


@pytest.mark.parametrize("direction", ["forward", "reverse", "fallback"])
def test_schema_accepts_valid_directions(handoff_schema, valid_handoff_payload, direction):
    """Garante aceitação dos 3 valores permitidos do enum direction."""
    payload = json.loads(json.dumps(valid_handoff_payload))
    payload["envelope"]["direction"] = direction
    jsonschema.validate(instance=payload, schema=handoff_schema)


@pytest.mark.parametrize("invalid_direction", ["sideways", "unknown", "inbound", ""])
def test_schema_rejects_invalid_directions(handoff_schema, valid_handoff_payload, invalid_direction):
    """Garante rejeição de valores inválidos no campo direction."""
    payload = json.loads(json.dumps(valid_handoff_payload))
    payload["envelope"]["direction"] = invalid_direction
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=handoff_schema)


def test_schema_requires_direction_field(handoff_schema, valid_handoff_payload):
    """Garante que a ausência do campo direction causa erro de validação."""
    payload = json.loads(json.dumps(valid_handoff_payload))
    del payload["envelope"]["direction"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=handoff_schema)


def test_create_and_validate_handoff_lifecycle(tmp_path):
    """Valida o ciclo de criação, persistência, leitura e validação via vitalia_handoff."""
    import vitalia_handoff

    storage_dir = tmp_path / "handoffs"
    storage_dir.mkdir(parents=True, exist_ok=True)

    handoff_file = vitalia_handoff.create_handoff(
        source_workflow="brainstorming",
        target_workflow="vitalia-route",
        intent_type="brainstorming_to_route",
        source_input="Testar ideação médica",
        normalized_summary="specs/kit-routing-subagents/research-brainstorming.md",
        direction="forward",
        storage_dir=storage_dir,
        feature_context="specs/kit-routing-subagents"
    )

    assert handoff_file.exists()
    assert handoff_file.name.startswith("handoff_brainstorming_to_vitalia-route_")
    assert handoff_file.name.endswith(".json")

    # Validação do arquivo gravado
    payload = vitalia_handoff.validate_handoff(handoff_file)
    assert payload["envelope"]["direction"] == "forward"
    assert payload["envelope"]["status"] == "pending"
    assert payload["intent"]["intent_type"] == "brainstorming_to_route"

    # Leitura do mais recente para o target
    latest = vitalia_handoff.latest_handoff(target_workflow="vitalia-route", storage_dir=storage_dir)
    assert latest is not None
    assert latest["envelope"]["handoff_id"] == payload["envelope"]["handoff_id"]

    # Consumo do handoff
    consumed = vitalia_handoff.consume_handoff(handoff_file)
    assert consumed["envelope"]["status"] == "consumed"

    # Após consumo, não deve mais retornar como pendente
    latest_after = vitalia_handoff.latest_handoff(target_workflow="vitalia-route", storage_dir=storage_dir)
    assert latest_after is None


def test_pre_hook_validation_latency_under_50ms(tmp_path):
    """Garante que a validação de handoff executa em menos de 50ms (SLO do hook runner)."""
    import vitalia_handoff

    storage_dir = tmp_path / "handoffs"
    storage_dir.mkdir(parents=True, exist_ok=True)

    handoff_file = vitalia_handoff.create_handoff(
        source_workflow="brainstorming",
        target_workflow="vitalia-route",
        intent_type="brainstorming_to_route",
        source_input="Benchmark de latência",
        normalized_summary="specs/kit-routing-subagents/research-brainstorming.md",
        direction="forward",
        storage_dir=storage_dir
    )

    start_time = time.perf_counter()
    vitalia_handoff.validate_handoff(handoff_file)
    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    assert elapsed_ms < 50.0, f"Latência de validação excessiva: {elapsed_ms:.2f}ms >= 50ms"


def test_cli_lifecycle_commands(tmp_path):
    """Valida a execução dos comandos CLI (create, validate, consume, latest)."""
    import subprocess

    storage_dir = tmp_path / "handoffs"
    storage_dir.mkdir(parents=True, exist_ok=True)

    # 1. CLI create
    cmd_create = [
        sys.executable,
        str(SRC_DIR / "vitalia_handoff.py"),
        "create",
        "--source", "brainstorming",
        "--target", "vitalia-route",
        "--direction", "forward",
        "--intent", "brainstorming_to_route",
        "--input", "Teste CLI create",
        "--summary", "specs/test.md",
        "--domain", "software",
        "--feature", "specs/feature-x"
    ]
    env = os.environ.copy()
    res_create = subprocess.run(cmd_create, capture_output=True, text=True, cwd=str(REPO_ROOT), env=env)
    assert res_create.returncode == 0, f"Erro no create CLI: {res_create.stderr}"
    created_info = json.loads(res_create.stdout)
    handoff_path = Path(created_info["file"])
    assert handoff_path.exists()
    assert created_info["direction"] == "forward"

    # 2. CLI validate
    cmd_val = [
        sys.executable,
        str(SRC_DIR / "vitalia_handoff.py"),
        "validate",
        "--file", str(handoff_path)
    ]
    res_val = subprocess.run(cmd_val, capture_output=True, text=True, cwd=str(REPO_ROOT), env=env)
    assert res_val.returncode == 0, f"Erro no validate CLI: {res_val.stderr}"

    # 3. CLI latest
    cmd_latest = [
        sys.executable,
        str(SRC_DIR / "vitalia_handoff.py"),
        "latest",
        "--target", "vitalia-route"
    ]
    res_latest = subprocess.run(cmd_latest, capture_output=True, text=True, cwd=str(REPO_ROOT), env=env)
    assert res_latest.returncode == 0
    assert str(handoff_path) in res_latest.stdout

    # 4. CLI consume
    cmd_con = [
        sys.executable,
        str(SRC_DIR / "vitalia_handoff.py"),
        "consume",
        "--file", str(handoff_path)
    ]
    res_con = subprocess.run(cmd_con, capture_output=True, text=True, cwd=str(REPO_ROOT), env=env)
    assert res_con.returncode == 0

    # Limpeza do arquivo de teste
    if handoff_path.exists():
        handoff_path.unlink()


