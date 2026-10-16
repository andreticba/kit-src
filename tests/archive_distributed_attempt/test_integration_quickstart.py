# test_integration_quickstart.py | Vitalia SDD v0.6.0 | 16-10-2026 05:57(GMT-04:00)
import os
import json
import time
import pytest
from pathlib import Path

from source.src.judge.services.redis_client import get_redis_client, check_redis_health
from source.src.judge.services.task_store import TaskStore
from source.src.judge.distributed_orchestrator import DistributedOrchestrator
from source.src.judge.hitl_resolver import HitlResolver


@pytest.fixture
def redis_client():
    if not check_redis_health():
        pytest.skip("Servidor Redis local não disponível para teste de integração Quickstart")
    return get_redis_client()


@pytest.fixture
def quickstart_fixture(tmp_path):
    content = """# Tasks: Exemplo Quickstart

## Fase 1: Setup e Infraestrutura
- [ ] T001 [P] [US1] Configurar cliente Redis em src/infra/redis_client.py com testes unitários em tests/test_redis.py

## Fase 2: Implementação de Core
- [ ] T002 [P] [US2] Implementar motor de FSM em src/core/fsm.py
- [ ] T003 [P] [US2] Modificar credenciais de produção no código de src/auth/keys.py
"""
    file_path = tmp_path / "sample_tasks.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path


def test_quickstart_end_to_end_flow(redis_client, quickstart_fixture, tmp_path):
    feature = f"test_quickstart_{int(time.time() * 1000)}"
    shards_dir = tmp_path / "shards"
    orchestrator = DistributedOrchestrator(
        feature=feature,
        tasks_path=str(quickstart_fixture),
        redis_client=redis_client,
        shards_dir=str(shards_dir),
        max_cycles=5,
        timeout_seconds=60,
    )

    store = TaskStore(redis_client=redis_client)
    try:
        # 1. Ingestão
        total = orchestrator.ingest_tasks()
        assert total == 3

        # 2. Simula adjudicação dos workers
        # T001 -> Aprovada direto
        store.record_adjudication(
            feature=feature,
            task_id="T001",
            verdict="APROVADA",
            rule_infringed=None,
            reasoning="Validado com testes unitários",
            evaluator_model="qwen2.5-coder:3b",
        )

        # T002 -> Ciclo 1 Reprovada, Ciclo 2 Contestada/Aprovada
        store.record_adjudication(
            feature=feature,
            task_id="T002",
            verdict="REPROVADA",
            rule_infringed="P05_TEST_FIRST",
            reasoning="Sem testes na linha",
            evaluator_model="qwen2.5-coder:3b",
        )
        store.record_adjudication(
            feature=feature,
            task_id="T002",
            verdict="APROVADA",
            rule_infringed=None,
            reasoning="Contestação aceita, componente puro",
            evaluator_model="qwen2.5-coder:3b",
            suggested_fix="- [ ] T002 [P] [US2] Implementar motor de FSM em src/core/fsm.py (aprovado)",
        )

        # T003 -> 5 ciclos de reprovação até ESCALADA_HITL
        for c in range(1, 6):
            store.record_adjudication(
                feature=feature,
                task_id="T003",
                verdict="REPROVADA",
                rule_infringed="P06_SECRETS",
                reasoning=f"Violação P06 no ciclo {c}",
                evaluator_model="qwen2.5-coder:3b",
            )

        # 3. Verifica detecção de escalação HITL
        has_hitl, escalated = orchestrator.check_hitl_escalation()
        assert has_hitl is True
        assert "T003" in escalated

        # 4. Resolução HITL via HitlResolver
        hitl = HitlResolver(feature=feature, redis_client=redis_client)
        new_text = "- [ ] T003 [P] [US2] Carregar chaves de autenticação exclusivamente a partir de variáveis de ambiente em src/auth/keys.py"
        inputs = iter(["3", new_text])
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("builtins.input", lambda _: next(inputs))
            resolved = hitl.resolve_task("T003")
            assert resolved is True

        # Verifica que agora T003 está APROVADA
        t3 = store.get_task(feature, "T003")
        assert t3["status"] == "APROVADA"
        assert t3["suggested_fix"] == new_text

        # 5. Verifica barreira 100% satisfeita
        assert orchestrator.check_barrier() is True

        # 6. Flush atômico
        assert orchestrator.flush_atomic() is True

        # 7. Verifica existência de backup e regravação
        backup = quickstart_fixture.parent / "sample_tasks.md.bak"
        assert backup.exists()
        updated_content = quickstart_fixture.read_text(encoding="utf-8")
        assert "Carregar chaves de autenticação exclusivamente a partir de variáveis de ambiente" in updated_content
        assert "Implementar motor de FSM em src/core/fsm.py (aprovado)" in updated_content

        # 8. Exportação de shard
        shard_file = orchestrator.export_session_shard()
        assert Path(shard_file).exists()
        shard_json = json.loads(Path(shard_file).read_text(encoding="utf-8"))
        assert shard_json["approved_tasks"] == 3
        assert shard_json["total_tasks"] == 3

    finally:
        redis_client.delete(store.get_task_key(feature, "T001"))
        redis_client.delete(store.get_task_key(feature, "T002"))
        redis_client.delete(store.get_task_key(feature, "T003"))
        redis_client.delete(store.get_index_key(feature))
