# test_config.py | Vitalia SDD v0.6.0 | 15-10-2026 22:01(GMT-04:00)
import os
import pytest
from unittest.mock import patch


def test_judge_config_defaults():
    with patch.dict(os.environ, {}, clear=True):
        from source.src.judge.config import JudgeConfig
        cfg = JudgeConfig.from_env()
        assert cfg.redis_url == "redis://localhost:6379/0"
        assert cfg.ollama_host == "http://localhost:11434"
        assert cfg.auditor_model == "qwen2.5-coder:3b"
        assert cfg.refactor_model == "qwen2.5-coder:3b"
        assert cfg.arbiter_model == "qwen2.5:3b"
        assert cfg.max_cycles == 5
        assert cfg.timeout_seconds == 180
        assert cfg.dry_run is False


def test_judge_config_custom_env():
    custom_env = {
        "REDIS_URL": "redis://redis.internal:6380/2",
        "OLLAMA_HOST": "http://192.168.1.50:11434",
        "VITALIA_AUDITOR_MODEL": "phi4-mini:latest",
        "VITALIA_REFACTOR_MODEL": "qwen2.5-coder:7b",
        "VITALIA_ARBITER_MODEL": "gemini-2.0-flash",
        "VITALIA_MAX_CYCLES": "8",
        "VITALIA_TIMEOUT_SECONDS": "240",
        "VITALIA_DRY_RUN": "1",
    }
    with patch.dict(os.environ, custom_env, clear=True):
        from source.src.judge.config import JudgeConfig
        cfg = JudgeConfig.from_env()
        assert cfg.redis_url == "redis://redis.internal:6380/2"
        assert cfg.ollama_host == "http://192.168.1.50:11434"
        assert cfg.auditor_model == "phi4-mini:latest"
        assert cfg.refactor_model == "qwen2.5-coder:7b"
        assert cfg.arbiter_model == "gemini-2.0-flash"
        assert cfg.max_cycles == 8
        assert cfg.timeout_seconds == 240
        assert cfg.dry_run is True


def test_judge_config_sanitize_secret():
    from source.src.judge.config import JudgeConfig
    # Verifica que representação string não vaza senhas contidas na URL
    cfg = JudgeConfig(redis_url="redis://default:supersecretpassword@localhost:6379/0")
    rep = str(cfg)
    assert "supersecretpassword" not in rep
    assert "***" in rep
