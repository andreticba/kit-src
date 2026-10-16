# test_distributed_orchestrator.py | Vitalia SDD v0.6.0 | 16-10-2026 05:54(GMT-04:00)
import os
import json
import time
import pytest
from pathlib import Path

from source.src.judge.services.redis_client import get_redis_client, check_redis_health
from source.src.judge.services.task_store import TaskStore
from source.src.judge.distributed_orchestrator import DistributedOrchestrator


@pytest.fixture
def redis_client():
    if not check_redis_health():
        pytest.skip("Servidor Redis local não disponível para teste do DistributedOrchestrator")
    return get_redis_client()


@pytest.fixture
def sample_tasks_file(tmp_path):
    tasks_content = """# Tasks

## Phase 1: Setup

- [ ] T001 [P] [US1] Criar módulo em src/core.py
- [ ] T002 [US1] Criar testes em tests/test_core.py
"""
    file_path = tmp_path / "tasks.md"
    file_path.write_text(tasks_content, encoding="utf-8")
    return file_path


def test_orchestrator_ingestion_and_barrier_blocks_when_pending(redis_client, sample_tasks_file, tmp_path):
    feature = f"test_orch_{int(time.time() * 1000)}"
    orchestrator = DistributedOrchestrator(
        feature=feature,
        tasks_path=str(sample_tasks_file),
        redis_client=redis_client,
        shards_dir=str(tmp_path / "shards"),
    )
    store = TaskStore(redis_client=redis_client)

    try:
        # Ingestão
        total_ingested = orchestrator.ingest_tasks()
        assert total_ingested == 2

        store = TaskStore(redis_client=redis_client)
        assert store.get_task(feature, "T001") is not None
        assert store.get_task(feature, "T002") is not None

        # Barreira antes da aprovação total
        is_ready = orchestrator.check_barrier()
        assert is_ready is False

        # Tentar flush enquanto pendente deve recusar e não alterar o disco
        flushed = orchestrator.flush_atomic()
        assert flushed is False
        assert not (sample_tasks_file.parent / "tasks.md.bak").exists()
        assert sample_tasks_file.read_text(encoding="utf-8") == """# Tasks

## Phase 1: Setup

- [ ] T001 [P] [US1] Criar módulo em src/core.py
- [ ] T002 [US1] Criar testes em tests/test_core.py
"""
    finally:
        redis_client.delete(store.get_task_key(feature, "T001"))
        redis_client.delete(store.get_task_key(feature, "T002"))
        redis_client.delete(store.get_index_key(feature))


def test_orchestrator_atomic_flush_and_backup(redis_client, sample_tasks_file, tmp_path):
    feature = f"test_flush_{int(time.time() * 1000)}"
    shards_dir = tmp_path / "shards"
    orchestrator = DistributedOrchestrator(
        feature=feature,
        tasks_path=str(sample_tasks_file),
        redis_client=redis_client,
        shards_dir=str(shards_dir),
    )

    store = TaskStore(redis_client=redis_client)
    try:
        orchestrator.ingest_tasks()

        # Aprova ambas as tarefas
        store.record_adjudication(
            feature=feature,
            task_id="T001",
            verdict="APROVADA",
            rule_infringed=None,
            reasoning="Validado com sucesso",
            evaluator_model="qwen2.5-coder:3b",
            suggested_fix="- [ ] T001 [P] [US1] Criar módulo em src/core.py (refatorado)",
        )
        store.record_adjudication(
            feature=feature,
            task_id="T002",
            verdict="APROVADA",
            rule_infringed=None,
            reasoning="Testes válidos",
            evaluator_model="qwen2.5-coder:3b",
        )

        assert orchestrator.check_barrier() is True

        # Executa flush atômico
        flushed = orchestrator.flush_atomic()
        assert flushed is True

        # Verifica criação do backup tasks.md.bak
        backup_file = sample_tasks_file.parent / "tasks.md.bak"
        assert backup_file.exists()
        assert "Criar módulo em src/core.py\n" in backup_file.read_text(encoding="utf-8")

        # Verifica escrita atômica do arquivo original com linhas atualizadas
        updated_content = sample_tasks_file.read_text(encoding="utf-8")
        assert "- [ ] T001 [P] [US1] Criar módulo em src/core.py (refatorado)" in updated_content
        assert "- [ ] T002 [US1] Criar testes em tests/test_core.py" in updated_content

        # Verifica exportação do shard de sessão
        shard_path = orchestrator.export_session_shard()
        assert shard_path is not None
        assert Path(shard_path).exists()

        shard_data = json.loads(Path(shard_path).read_text(encoding="utf-8"))
        assert shard_data["feature"] == feature
        assert shard_data["total_tasks"] == 2
        assert shard_data["approved_tasks"] == 2
        assert len(shard_data["tasks"]) == 2

    finally:
        redis_client.delete(store.get_task_key(feature, "T001"))
        redis_client.delete(store.get_task_key(feature, "T002"))
        redis_client.delete(store.get_index_key(feature))


def test_orchestrator_detects_hitl_escalation(redis_client, sample_tasks_file, tmp_path):
    feature = f"test_orch_hitl_{int(time.time() * 1000)}"
    orchestrator = DistributedOrchestrator(
        feature=feature,
        tasks_path=str(sample_tasks_file),
        redis_client=redis_client,
        shards_dir=str(tmp_path / "shards"),
    )

    store = TaskStore(redis_client=redis_client)
    try:
        orchestrator.ingest_tasks()

        # Simula escalação HITL na T001
        for _ in range(5):
            store.record_adjudication(
                feature=feature,
                task_id="T001",
                verdict="REPROVADA",
                rule_infringed="P05_TEST_FIRST",
                reasoning="Sem testes",
                evaluator_model="qwen2.5-coder:3b",
            )

        has_hitl, escalated_ids = orchestrator.check_hitl_escalation()
        assert has_hitl is True
        assert "T001" in escalated_ids

    finally:
        redis_client.delete(store.get_task_key(feature, "T001"))
        redis_client.delete(store.get_task_key(feature, "T002"))
        redis_client.delete(store.get_index_key(feature))
