# test_base_worker.py | Vitalia SDD v0.6.0 | 16-10-2026 05:45(GMT-04:00)
import time
import pytest
from unittest.mock import MagicMock
from source.src.judge.services.redis_client import get_redis_client, check_redis_health


@pytest.fixture
def redis_client():
    if not check_redis_health():
        pytest.skip("Servidor Redis local não disponível para teste do BaseWorker")
    return get_redis_client()


def test_base_worker_run_once_acknowledges_on_success(redis_client):
    from source.src.judge.workers.base_worker import BaseWorker
    from source.src.judge.services.stream_broker import StreamBroker
    from source.src.judge.services.task_store import TaskStore

    feature = f"test_worker_{int(time.time() * 1000)}"
    broker = StreamBroker(redis_client=redis_client)
    store = TaskStore(redis_client=redis_client)
    group_name = "test_worker_group"

    broker.ensure_consumer_group(feature, group_name)

    # Cria subclasse de teste concreta
    processed = []

    class ConcreteWorker(BaseWorker):
        def process_event(self, event):
            processed.append(event["task_id"])
            return True

    worker = ConcreteWorker(
        feature=feature,
        group_name=group_name,
        consumer_name="worker_test_1",
        broker=broker,
        store=store,
    )

    try:
        broker.publish_event(
            feature=feature,
            event_type="TASK_INGESTED",
            task_id="T001",
            payload={"action": "test"},
            producer="test",
        )

        count = worker.run_once(block_ms=500)
        assert count == 1
        assert processed == ["T001"]

        # Segunda leitura não deve trazer o mesmo evento pois foi confirmado com ACK
        count_again = worker.run_once(block_ms=100)
        assert count_again == 0

    finally:
        redis_client.delete(broker.get_stream_key(feature))
