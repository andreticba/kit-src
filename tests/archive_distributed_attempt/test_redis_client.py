# test_redis_client.py | Vitalia SDD v0.6.0 | 16-10-2026 05:20(GMT-04:00)
import os
import pytest
from unittest.mock import patch, MagicMock


def test_get_redis_client_uses_decode_responses():
    """Gotcha 1: Conexão DEVE configurar decode_responses=True para evitar bytes."""
    with patch("redis.ConnectionPool.from_url") as mock_pool, \
         patch("redis.Redis") as mock_redis:
        from source.src.judge.services.redis_client import get_redis_client
        client = get_redis_client(redis_url="redis://localhost:6379/1")

        mock_pool.assert_called_once()
        _, kwargs = mock_pool.call_args
        assert kwargs.get("decode_responses") is True


def test_get_redis_client_url_from_env():
    with patch.dict(os.environ, {"REDIS_URL": "redis://custom.host:6380/3"}):
        with patch("redis.ConnectionPool.from_url") as mock_pool, \
             patch("redis.Redis") as mock_redis:
            from source.src.judge.services.redis_client import get_redis_client
            get_redis_client()

            args, _ = mock_pool.call_args
            assert args[0] == "redis://custom.host:6380/3"


def test_redis_client_health_check_success():
    with patch("redis.ConnectionPool.from_url"), \
         patch("redis.Redis") as mock_redis:
        mock_instance = MagicMock()
        mock_instance.ping.return_value = True
        mock_redis.return_value = mock_instance

        from source.src.judge.services.redis_client import check_redis_health
        is_healthy = check_redis_health(redis_url="redis://localhost:6379/0")
        assert is_healthy is True


def test_redis_client_health_check_failure():
    with patch("redis.ConnectionPool.from_url"), \
         patch("redis.Redis") as mock_redis:
        import redis
        mock_instance = MagicMock()
        mock_instance.ping.side_effect = redis.exceptions.ConnectionError("Connection refused")
        mock_redis.return_value = mock_instance

        from source.src.judge.services.redis_client import check_redis_health
        is_healthy = check_redis_health(redis_url="redis://localhost:6379/0")
        assert is_healthy is False
