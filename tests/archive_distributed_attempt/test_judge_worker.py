# test_judge_worker.py | Vitalia SDD v0.6.0 | 16-10-2026 05:47(GMT-04:00)
import time
import pytest
from unittest.mock import MagicMock
from source.src.judge.services.redis_client import get_redis_client, check_redis_health
from source.src.judge.envelope_parser import TaskEnvelope


@pytest.fixture
def redis_client():
    if not check_redis_health():
        pytest.skip("Servidor Redis local não disponível para teste do JudgeWorker")
    return get_redis_client()


def test_judge_worker_approves_compliant_task(redis_client):
    from source.src.judge.workers.judge_worker import JudgeWorker
    from source.src.judge.services.stream_broker import StreamBroker
    from source.src.judge.services.task_store import TaskStore

    feature = f"test_judge_appr_{int(time.time() * 1000)}"
    broker = StreamBroker(redis_client=redis_client)
    store = TaskStore(redis_client=redis_client)

    envelope = TaskEnvelope(
        task_id="T001",
        raw_line="- [ ] T001 [P] [US1] Criar testes unitários em tests/test_core.py",
        phase_name="Fase 1: Setup",
        user_story={"id": "US1", "title": "Setup", "acceptance_criteria": []},
        target_component="tests/test_core.py",
        test_task_predecessor=None,
        negative_scope_flags={"contains_secrets": False, "touches_security_core": False, "production_deployment": False},
        contextual_files_referenced=["tests/test_core.py"],
    )

    store.ingest_task(feature, envelope)

    worker = JudgeWorker(
        feature=feature,
        consumer_name="judge_test_1",
        broker=broker,
        store=store,
    )

    try:
        broker.publish_event(
            feature=feature,
            event_type="TASK_INGESTED",
            task_id="T001",
            payload={"action": "audit"},
            producer="orchestrator",
        )

        count = worker.run_once(block_ms=500)
        assert count == 1

        task = store.get_task(feature, "T001")
        assert task["status"] == "APROVADA"
        assert task["cycle_count"] == 1

    finally:
        redis_client.delete(broker.get_stream_key(feature))
        redis_client.delete(store.get_task_key(feature, "T001"))


def test_judge_worker_rejects_task_with_secrets(redis_client):
    from source.src.judge.workers.judge_worker import JudgeWorker
    from source.src.judge.services.stream_broker import StreamBroker
    from source.src.judge.services.task_store import TaskStore

    feature = f"test_judge_sec_{int(time.time() * 1000)}"
    broker = StreamBroker(redis_client=redis_client)
    store = TaskStore(redis_client=redis_client)

    envelope = TaskEnvelope(
        task_id="T002",
        raw_line='- [ ] T002 [US1] Adicionar senha password="admin" em src/auth.py',
        phase_name="Fase 1: Setup",
        user_story={"id": "US1", "title": "Setup", "acceptance_criteria": []},
        target_component="src/auth.py",
        test_task_predecessor=None,
        negative_scope_flags={"contains_secrets": True, "touches_security_core": True, "production_deployment": False},
        contextual_files_referenced=["src/auth.py"],
    )

    store.ingest_task(feature, envelope)

    worker = JudgeWorker(
        feature=feature,
        consumer_name="judge_test_2",
        broker=broker,
        store=store,
    )

    try:
        broker.publish_event(
            feature=feature,
            event_type="TASK_INGESTED",
            task_id="T002",
            payload={"action": "audit"},
            producer="orchestrator",
        )

        count = worker.run_once(block_ms=500)
        assert count == 1

        task = store.get_task(feature, "T002")
        assert task["status"] == "REPROVADA"
        assert task["history"][-1]["rule_infringed"] == "P06_SECRETS"

    finally:
        redis_client.delete(broker.get_stream_key(feature))
        redis_client.delete(store.get_task_key(feature, "T002"))
