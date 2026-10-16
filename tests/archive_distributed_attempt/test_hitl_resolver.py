# test_hitl_resolver.py | Vitalia SDD v0.6.0 | 16-10-2026 05:51(GMT-04:00)
import time
import pytest
from unittest.mock import patch
from source.src.judge.services.redis_client import get_redis_client, check_redis_health
from source.src.judge.envelope_parser import TaskEnvelope


@pytest.fixture
def redis_client():
    if not check_redis_health():
        pytest.skip("Servidor Redis local não disponível para teste do HitlResolver")
    return get_redis_client()


def test_hitl_resolver_approve_proposed_fix(redis_client):
    from source.src.judge.hitl_resolver import HitlResolver
    from source.src.judge.services.stream_broker import StreamBroker
    from source.src.judge.services.task_store import TaskStore

    feature = f"test_hitl_{int(time.time() * 1000)}"
    broker = StreamBroker(redis_client=redis_client)
    store = TaskStore(redis_client=redis_client)

    envelope = TaskEnvelope(
        task_id="T005",
        raw_line="- [ ] T005 [P] [US2] Implementar listener em src/services/consumer.py",
        phase_name="Fase 2",
        user_story={"id": "US2", "title": "Streams", "acceptance_criteria": []},
        target_component="src/services/consumer.py",
        test_task_predecessor=None,
        negative_scope_flags={"contains_secrets": False, "touches_security_core": False, "production_deployment": False},
        contextual_files_referenced=["src/services/consumer.py"],
    )

    store.ingest_task(feature, envelope)
    # Coloca status em ESCALADA_HITL
    store.update_status(
        feature=feature,
        task_id="T005",
        new_status="ESCALADA_HITL",
        suggested_fix="- [ ] T005 [P] [US2] Implementar listener em src/services/consumer.py satisfazendo tests/test_consumer.py",
        escalation_reason="Deadlock após 5 ciclos",
    )

    resolver = HitlResolver(feature=feature, broker=broker, store=store)

    # Simula seleção da opção 1 (Aprovar proposta do refatorador)
    with patch("builtins.input", return_value="1"):
        success = resolver.resolve_task("T005")
        assert success is True

    task = store.get_task(feature, "T005")
    assert task["status"] == "APROVADA"
    assert "tests/test_consumer.py" in task["suggested_fix"]

    redis_client.delete(broker.get_stream_key(feature))
    redis_client.delete(store.get_task_key(feature, "T005"))


def test_hitl_resolver_manual_edit(redis_client):
    from source.src.judge.hitl_resolver import HitlResolver
    from source.src.judge.services.stream_broker import StreamBroker
    from source.src.judge.services.task_store import TaskStore

    feature = f"test_hitl_edit_{int(time.time() * 1000)}"
    broker = StreamBroker(redis_client=redis_client)
    store = TaskStore(redis_client=redis_client)

    envelope = TaskEnvelope(
        task_id="T007",
        raw_line="- [ ] T007 [P] [US2] Linha problemática",
        phase_name="Fase 2",
        user_story={"id": "US2", "title": "Streams", "acceptance_criteria": []},
        target_component="src/services/consumer.py",
        test_task_predecessor=None,
        negative_scope_flags={"contains_secrets": False, "touches_security_core": False, "production_deployment": False},
        contextual_files_referenced=[],
    )

    store.ingest_task(feature, envelope)
    store.update_status(feature, "T007", "ESCALADA_HITL")

    resolver = HitlResolver(feature=feature, broker=broker, store=store)

    # Simula opção 3 (editar manualmente) e digita nova linha
    inputs = iter(["3", "- [ ] T007 [P] [US2] Linha corrigida manualmente pelo desenvolvedor em src/code.py"])
    with patch("builtins.input", lambda _: next(inputs)):
        success = resolver.resolve_task("T007")
        assert success is True

    task = store.get_task(feature, "T007")
    assert task["status"] == "APROVADA"
    assert "corrigida manualmente" in task["suggested_fix"]

    redis_client.delete(broker.get_stream_key(feature))
    redis_client.delete(store.get_task_key(feature, "T007"))
