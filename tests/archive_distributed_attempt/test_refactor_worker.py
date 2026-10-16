# test_refactor_worker.py | Vitalia SDD v0.6.0 | 16-10-2026 05:50(GMT-04:00)
import time
import pytest
from source.src.judge.services.redis_client import get_redis_client, check_redis_health
from source.src.judge.envelope_parser import TaskEnvelope


@pytest.fixture
def redis_client():
    if not check_redis_health():
        pytest.skip("Servidor Redis local não disponível para teste do RefactorWorker")
    return get_redis_client()


def test_refactor_worker_rewrites_task_and_publishes_refactored(redis_client):
    from source.src.judge.workers.refactor_worker import RefactorWorker
    from source.src.judge.services.stream_broker import StreamBroker
    from source.src.judge.services.task_store import TaskStore

    feature = f"test_refactor_{int(time.time() * 1000)}"
    broker = StreamBroker(redis_client=redis_client)
    store = TaskStore(redis_client=redis_client)

    envelope = TaskEnvelope(
        task_id="T005",
        raw_line="- [ ] T005 [P] [US2] Implementar listener em src/services/consumer.py",
        phase_name="Fase 2: Motor Redis",
        user_story={"id": "US2", "title": "Streams", "acceptance_criteria": []},
        target_component="src/services/consumer.py",
        test_task_predecessor={"task_id": "T004", "raw_line": "- [ ] T004 Criar testes em tests/test_consumer.py", "is_completed": False},
        negative_scope_flags={"contains_secrets": False, "touches_security_core": False, "production_deployment": False},
        contextual_files_referenced=["src/services/consumer.py", "tests/test_consumer.py"],
    )

    store.ingest_task(feature, envelope)
    # Ciclo 1
    store.record_adjudication(
        feature=feature,
        task_id="T005",
        verdict="REPROVADA",
        rule_infringed="P05_TEST_FIRST",
        reasoning="Sem menção textual a testes",
        evaluator_model="qwen2.5-coder:3b",
    )

    worker = RefactorWorker(
        feature=feature,
        consumer_name="refactor_test_1",
        broker=broker,
        store=store,
    )

    try:
        broker.publish_event(
            feature=feature,
            event_type="TASK_CONTESTED",
            task_id="T005",
            payload={"counter_argument": "Explicitar testes/test_consumer.py", "cycle": 1},
            producer="contesta_1",
        )

        count = worker.run_once(block_ms=500)
        assert count == 1

        # Deve publicar TASK_REFACTORED de volta para o Juiz
        events = broker.read_events(
            feature=feature,
            group_name="juiz_group",
            consumer_name="test_checker",
            count=5,
            block_ms=500,
        )
        refactored_event = next((e for e in events if e["event_type"] == "TASK_REFACTORED"), None)
        assert refactored_event is not None
        assert refactored_event["task_id"] == "T005"

        task = store.get_task(feature, "T005")
        assert "tests/test_consumer.py" in task["suggested_fix"]

    finally:
        redis_client.delete(broker.get_stream_key(feature))
        redis_client.delete(store.get_task_key(feature, "T005"))


def test_refactor_worker_escalates_on_fifth_cycle(redis_client):
    from source.src.judge.workers.refactor_worker import RefactorWorker
    from source.src.judge.services.stream_broker import StreamBroker
    from source.src.judge.services.task_store import TaskStore

    feature = f"test_escalate_worker_{int(time.time() * 1000)}"
    broker = StreamBroker(redis_client=redis_client)
    store = TaskStore(redis_client=redis_client)

    envelope = TaskEnvelope(
        task_id="T009",
        raw_line="- [ ] T009 Conflito irresolvível em src/deadlock.py",
        phase_name="Fase 2",
        user_story={"id": "US2", "title": "Deadlock", "acceptance_criteria": []},
        target_component="src/deadlock.py",
        test_task_predecessor=None,
        negative_scope_flags={"contains_secrets": True, "touches_security_core": True, "production_deployment": False},
        contextual_files_referenced=["src/deadlock.py"],
    )

    store.ingest_task(feature, envelope)
    # Simula avanço para 5 ciclos
    for _ in range(5):
        store.record_adjudication(
            feature=feature,
            task_id="T009",
            verdict="REPROVADA",
            rule_infringed="P06_SECRETS",
            reasoning="Conflito persistente",
            evaluator_model="qwen2.5-coder:3b",
        )

    worker = RefactorWorker(
        feature=feature,
        consumer_name="refactor_test_2",
        broker=broker,
        store=store,
    )

    try:
        broker.publish_event(
            feature=feature,
            event_type="TASK_CONTESTED",
            task_id="T009",
            payload={"counter_argument": "Tentativa 5", "cycle": 5},
            producer="contesta_1",
        )

        count = worker.run_once(block_ms=500)
        assert count == 1

        task = store.get_task(feature, "T009")
        assert task["status"] == "ESCALADA_HITL"

        # Deve publicar TASK_ESCALATED para o grupo HITL
        events = broker.read_events(
            feature=feature,
            group_name="hitl_group",
            consumer_name="hitl_checker",
            count=5,
            block_ms=500,
        )
        escalated_event = next((e for e in events if e["event_type"] == "TASK_ESCALATED"), None)
        assert escalated_event is not None
        assert escalated_event["task_id"] == "T009"

    finally:
        redis_client.delete(broker.get_stream_key(feature))
        redis_client.delete(store.get_task_key(feature, "T009"))
