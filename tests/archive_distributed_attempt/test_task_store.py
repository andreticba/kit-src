# test_task_store.py | Vitalia SDD v0.6.0 | 16-10-2026 05:43(GMT-04:00)
import time
import pytest
from source.src.judge.services.redis_client import get_redis_client, check_redis_health
from source.src.judge.envelope_parser import TaskEnvelope


@pytest.fixture
def redis_client():
    if not check_redis_health():
        pytest.skip("Servidor Redis local não disponível para teste de integração do TaskStore")
    return get_redis_client()


@pytest.fixture
def sample_envelope():
    return TaskEnvelope(
        task_id="T001",
        raw_line="- [ ] T001 [P] [US1] Criar módulo em src/core.py",
        phase_name="Fase 1: Setup",
        user_story={"id": "US1", "title": "Setup", "acceptance_criteria": []},
        target_component="src/core.py",
        test_task_predecessor=None,
        negative_scope_flags={"contains_secrets": False, "touches_security_core": False, "production_deployment": False},
        contextual_files_referenced=["src/core.py"],
    )


def test_task_store_ingest_and_retrieve(redis_client, sample_envelope):
    from source.src.judge.services.task_store import TaskStore

    feature = f"test_store_{int(time.time() * 1000)}"
    store = TaskStore(redis_client=redis_client)

    try:
        store.ingest_task(feature, sample_envelope)

        task = store.get_task(feature, "T001")
        assert task is not None
        assert task["task_id"] == "T001"
        assert task["status"] == "PENDENTE"
        assert task["cycle_count"] == 0
        assert task["is_parallel"] is True
        assert task["envelope"]["task_id"] == "T001"
        assert task["history"] == []

        # Verificar TTL positivo (Gotcha / NFR)
        key = store.get_task_key(feature, "T001")
        ttl = redis_client.ttl(key)
        assert ttl > 0

    finally:
        redis_client.delete(store.get_task_key(feature, "T001"))


def test_task_store_adjudication_cycle_and_fsm(redis_client, sample_envelope):
    from source.src.judge.services.task_store import TaskStore

    feature = f"test_fsm_{int(time.time() * 1000)}"
    store = TaskStore(redis_client=redis_client)

    try:
        store.ingest_task(feature, sample_envelope)

        # Ciclo 1: Reprovação
        store.record_adjudication(
            feature=feature,
            task_id="T001",
            verdict="REPROVADA",
            rule_infringed="P05_TEST_FIRST",
            reasoning="Sem testes prévios declarados",
            evaluator_model="qwen2.5-coder:3b",
        )
        task = store.get_task(feature, "T001")
        assert task["status"] == "REPROVADA"
        assert task["cycle_count"] == 1
        assert len(task["history"]) == 1

        # Ciclo 2: Contestação aceita e aprovação
        store.record_adjudication(
            feature=feature,
            task_id="T001",
            verdict="APROVADA",
            rule_infringed=None,
            reasoning="Dependência esclarecida",
            evaluator_model="qwen2.5-coder:3b",
            suggested_fix="- [ ] T001 [P] [US1] Criar módulo em src/core.py com testes em tests/test_core.py",
        )
        task = store.get_task(feature, "T001")
        assert task["status"] == "APROVADA"
        assert task["cycle_count"] == 2
        assert len(task["history"]) == 2
        assert "tests/test_core.py" in task["suggested_fix"]

        # Barreira de Sincronização
        is_complete, approved, total = store.check_completion_barrier(feature)
        assert is_complete is True
        assert approved == 1
        assert total == 1

    finally:
        redis_client.delete(store.get_task_key(feature, "T001"))


def test_task_store_escalates_at_five_cycles(redis_client, sample_envelope):
    from source.src.judge.services.task_store import TaskStore

    feature = f"test_escalate_{int(time.time() * 1000)}"
    store = TaskStore(redis_client=redis_client)

    try:
        store.ingest_task(feature, sample_envelope)

        # Simula 5 ciclos de reprovação
        for c in range(1, 6):
            store.record_adjudication(
                feature=feature,
                task_id="T001",
                verdict="REPROVADA",
                rule_infringed="P06_SECRETS",
                reasoning=f"Violação ciclo {c}",
                evaluator_model="qwen2.5-coder:3b",
            )

        task = store.get_task(feature, "T001")
        assert task["cycle_count"] == 5
        assert task["status"] == "ESCALADA_HITL"

    finally:
        redis_client.delete(store.get_task_key(feature, "T001"))
