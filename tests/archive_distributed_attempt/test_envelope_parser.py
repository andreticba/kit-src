# test_envelope_parser.py | Vitalia SDD v0.6.0 | 16-10-2026 05:24(GMT-04:00)
import json
from pathlib import Path
import pytest
import jsonschema


SAMPLE_TASKS_MD = """# Tasks: Test Feature

## Phase 1: Setup & Configurações
- [ ] T001 [P] Criar testes unitários em tests/test_config.py
- [ ] T002 Implementar configuração em source/src/judge/config.py

## Phase 3: User Story 1 — Parser Sintético
**Story Goal**: Transformar linhas isoladas em envelopes.
**Independent Test**: Executar pytest tests/test_parser.py

- [ ] T010 [P] [US1] Criar testes unitários em tests/test_envelope_parser.py
- [ ] T011 [US1] Implementar parser sintático em source/src/judge/envelope_parser.py
- [ ] T012 [US1] Inserir senha secreta password="12345" em source/src/auth.py
"""


@pytest.fixture
def envelope_schema():
    schema_path = Path("specs/sdd-judge-distributed/contracts/envelope-schema.json")
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_parser_extracts_all_tasks(envelope_schema):
    from source.src.judge.envelope_parser import TaskEnvelopeParser
    parser = TaskEnvelopeParser(SAMPLE_TASKS_MD)
    envelopes = parser.parse_all()

    assert len(envelopes) == 5
    ids = [e.task_id for e in envelopes]
    assert ids == ["T001", "T002", "T010", "T011", "T012"]


def test_parser_associates_predecessor_test_task(envelope_schema):
    from source.src.judge.envelope_parser import TaskEnvelopeParser
    parser = TaskEnvelopeParser(SAMPLE_TASKS_MD)
    envelopes = parser.parse_all()

    # T011 é tarefa produtiva de US1; seu predecessor de teste deve ser T010
    t011 = next(e for e in envelopes if e.task_id == "T011")
    assert t011.test_task_predecessor is not None
    assert t011.test_task_predecessor["task_id"] == "T010"
    assert "tests/test_envelope_parser.py" in t011.test_task_predecessor["raw_line"]

    # Validação contra o JSON Schema oficial
    d = t011.to_dict()
    jsonschema.validate(instance=d, schema=envelope_schema)


def test_parser_detects_negative_scope_flags(envelope_schema):
    from source.src.judge.envelope_parser import TaskEnvelopeParser
    parser = TaskEnvelopeParser(SAMPLE_TASKS_MD)
    envelopes = parser.parse_all()

    # T011 é limpa
    t011 = next(e for e in envelopes if e.task_id == "T011")
    assert t011.negative_scope_flags["contains_secrets"] is False

    # T012 contém literal password="..."
    t012 = next(e for e in envelopes if e.task_id == "T012")
    assert t012.negative_scope_flags["contains_secrets"] is True


def test_parser_extracts_target_component():
    from source.src.judge.envelope_parser import TaskEnvelopeParser
    parser = TaskEnvelopeParser(SAMPLE_TASKS_MD)
    envelopes = parser.parse_all()

    t001 = next(e for e in envelopes if e.task_id == "T001")
    assert t001.target_component == "tests/test_config.py"

    t011 = next(e for e in envelopes if e.task_id == "T011")
    assert t011.target_component == "source/src/judge/envelope_parser.py"
