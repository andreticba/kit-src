# test_stream_broker.py | Vitalia SDD v0.6.0 | 16-10-2026 05:41(GMT-04:00)
import time
import pytest
from source.src.judge.services.redis_client import get_redis_client, check_redis_health


@pytest.fixture
def redis_client():
    if not check_redis_health():
        pytest.skip("Servidor Redis local não disponível para teste de integração de streams")
    client = get_redis_client()
    return client


def test_stream_broker_lifecycle(redis_client):
    from source.src.judge.services.stream_broker import StreamBroker

    feature = f"test_feat_{int(time.time() * 1000)}"
    broker = StreamBroker(redis_client=redis_client)
    stream_key = broker.get_stream_key(feature)

    try:
        # 1. Criação idempotente de Consumer Group (Gotcha 2)
        group_name = "test_judge_group"
        broker.ensure_consumer_group(feature, group_name)
        # Segunda chamada deve ser idempotente e não estourar BUSYGROUP
        broker.ensure_consumer_group(feature, group_name)

        # 2. Publicação de evento
        event_id = broker.publish_event(
            feature=feature,
            event_type="TASK_INGESTED",
            task_id="T001",
            payload={"phase": "Setup", "action": "audit"},
            producer="orchestrator",
        )
        assert event_id is not None
        assert "-" in event_id

        # 3. Leitura via Consumer Group
        events = broker.read_events(
            feature=feature,
            group_name=group_name,
            consumer_name="consumer_1",
            count=1,
            block_ms=1000,
        )
        assert len(events) == 1
        ev = events[0]
        assert ev["event_id"] == event_id
        assert ev["event_type"] == "TASK_INGESTED"
        assert ev["task_id"] == "T001"
        assert ev["payload"]["phase"] == "Setup"

        # 4. Confirmação ACK
        ack_count = broker.ack_event(feature, group_name, event_id)
        assert ack_count == 1

    finally:
        redis_client.delete(stream_key)
