# test_contest_worker.py | Vitalia SDD v0.6.0 | 16-10-2026 05:48(GMT-04:00)
import time
import pytest
from source.src.judge.services.redis_client import get_redis_client, check_redis_health
from source.src.judge.envelope_parser import TaskEnvelope


@pytest.fixture
def redis_client():
    if not check_redis_health():
        pytest.skip("Servidor Redis local não disponível para teste do ContestWorker")
    return get_redis_client()


def test_contest_worker_analyzes_rejection_and_publishes_defense(redis_client):
    from source.src.judge.workers.contest_worker import ContestWorker
    from source.src.judge.services.stream_broker import StreamBroker
    from source.src.judge.services.task_store import TaskStore

    feature = f"test_contest_{int(time.time() * 1000)}"
    broker = StreamBroker(redis_client=redis_client)
    store = TaskStore(redis_client=redis_client)

    envelope = TaskEnvelope(
        task_id="T005",
        raw_line="- [ ] T005 [P] [US2] Implementar listener de stream em src/services/consumer.py",
        phase_name="Fase 2: Motor Redis",
        user_story={"id": "US2", "title": "Streams", "acceptance_criteria": []},
        target_component="src/services/consumer.py",
        test_task_predecessor=None,
        negative_scope_flags={"contains_secrets": False, "touches_security_core": False, "production_deployment": False},
        contextual_files_referenced=["src/services/consumer.py"],
    )

    store.ingest_task(feature, envelope)
    store.record_adjudication(
        feature=feature,
        task_id="T005",
        verdict="REPROVADA",
        rule_infringed="P05_TEST_FIRST",
        reasoning="Tarefa produtiva sem teste explícito",
        evaluator_model="qwen2.5-coder:3b",
    )

    worker = ContestWorker(
        feature=feature,
        consumer_name="contest_test_1",
        broker=broker,
        store=store,
    )

    try:
        broker.publish_event(
            feature=feature,
            event_type="TASK_ADJUDICATED",
            task_id="T005",
            payload={"status": "REPROVADA", "rule_infringed": "P05_TEST_FIRST"},
            producer="juiz_1",
        )

        count = worker.run_once(block_ms=500)
        assert count == 1

        # Verifica se publicou TASK_CONTESTED para o Refatorador
        events = broker.read_events(
            feature=feature,
            group_name="refatura_group",
            consumer_name="test_checker",
            count=5,
            block_ms=500,
        )
        contested_event = next((e for e in events if e["event_type"] == "TASK_CONTESTED"), None)
        assert contested_event is not None
        assert contested_event["task_id"] == "T005"
        assert "counter_argument" in contested_event["payload"]


    finally:
        redis_client.delete(broker.get_stream_key(feature))
        redis_client.delete(store.get_task_key(feature, "T005"))
