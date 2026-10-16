# test_envelope_schema.py | Vitalia SDD v0.6.0 | 15-10-2026 22:36(GMT-04:00)
import json
from pathlib import Path
import pytest
import jsonschema


@pytest.fixture
def envelope_schema():
    schema_path = Path("specs/sdd-judge-distributed/contracts/envelope-schema.json")
    assert schema_path.exists(), f"Schema não encontrado em {schema_path}"
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def valid_envelope():
    return {
        "task_id": "T005",
        "raw_line": "- [ ] T005 [P] [US2] Criar serviço RedisStreamConsumer em src/services/consumer.py",
        "phase_name": "Fase 2: Motor Redis & FSM",
        "user_story": {
            "id": "US2",
            "title": "Adjudicação Concorrente via Consumer Groups",
            "acceptance_criteria": [
                "Processar mensagens simultâneas sem race condition",
                "Garantir ACK apenas após validação completa"
            ]
        },
        "target_component": "src/services/consumer.py",
        "test_task_predecessor": {
            "task_id": "T004",
            "raw_line": "- [ ] T004 [P] [US2] Criar testes em tests/test_consumer.py",
            "is_completed": False
        },
        "negative_scope_flags": {
            "contains_secrets": False,
            "touches_security_core": False,
            "production_deployment": False
        },
        "contextual_files_referenced": [
            "src/services/consumer.py",
            "tests/test_consumer.py"
        ]
    }


def test_envelope_schema_valid_payload(envelope_schema, valid_envelope):
    jsonschema.validate(instance=valid_envelope, schema=envelope_schema)


def test_envelope_schema_null_predecessor(envelope_schema, valid_envelope):
    valid_envelope["test_task_predecessor"] = None
    jsonschema.validate(instance=valid_envelope, schema=envelope_schema)


def test_envelope_schema_missing_required_field(envelope_schema, valid_envelope):
    del valid_envelope["task_id"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=valid_envelope, schema=envelope_schema)


def test_envelope_schema_invalid_task_id(envelope_schema, valid_envelope):
    valid_envelope["task_id"] = "INVALID_TASK_99"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=valid_envelope, schema=envelope_schema)


def test_envelope_schema_missing_negative_scope(envelope_schema, valid_envelope):
    del valid_envelope["negative_scope_flags"]["contains_secrets"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=valid_envelope, schema=envelope_schema)
