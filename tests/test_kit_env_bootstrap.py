# test_kit_env_bootstrap.py | Vitalia SDD v0.6.0 | 16-10-2026 16:55(GMT-04:00)
import os
import sys
import tempfile
from pathlib import Path
import pytest

from source.src.kit_env_bootstrap import (
    find_project_root,
    load_dotenv_native,
    inject_venv,
    check_environment_health,
)


def test_find_project_root_indicator():
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        (root / ".git").mkdir()
        sub = root / "src" / "deep" / "nested"
        sub.mkdir(parents=True)

        found = find_project_root(sub)
        assert found == root


def test_find_project_root_vitalia():
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        (root / ".vitalia").mkdir()
        sub = root / "specs" / "feature"
        sub.mkdir(parents=True)

        found = find_project_root(sub)
        assert found == root


def test_load_dotenv_native():
    with tempfile.TemporaryDirectory() as tmp_dir:
        env_file = Path(tmp_dir) / ".env"
        env_file.write_text(
            """
            # Comentário de teste
            FOO=bar
            export BAZ="qux"
            WITH_COMMENT=val # ignore this
            SPACED = simple value
            """,
            encoding="utf-8",
        )

        loaded = load_dotenv_native(env_file, override=True)
        assert loaded["FOO"] == "bar"
        assert loaded["BAZ"] == "qux"
        assert loaded["WITH_COMMENT"] == "val"
        assert loaded["SPACED"] == "simple value"
        assert os.environ.get("FOO") == "bar"


def test_inject_venv():
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        site_packages = root / ".venv" / "lib" / "python3.14" / "site-packages"
        site_packages.mkdir(parents=True)

        success, path_str = inject_venv(root)
        assert success is True
        assert path_str == str(site_packages.resolve())
        assert str(site_packages.resolve()) in sys.path


def test_check_environment_health_structure():
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        health = check_environment_health(root)
        assert "status" in health
        assert "project_root" in health
        assert "has_env" in health
        assert "venv_ok" in health
