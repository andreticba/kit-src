# test_kit_bootstrap_safeguards.py | Vitalia SDD v0.6.0 | 16-10-2026 16:55(GMT-04:00)
import os
import subprocess
import tempfile
from pathlib import Path
import pytest


def test_bootstrap_dry_run():
    script = Path(__file__).parent.parent / "kit-bootstrap.sh"
    assert script.exists()

    result = subprocess.run(
        ["bash", str(script), "--dry-run"],
        capture_output=True,
        text=True,
        cwd=str(script.parent),
    )
    assert result.returncode == 0
    assert "[DRY-RUN]" in result.stdout or "[DRY]" in result.stdout


def test_bootstrap_safeguards_existing_env_and_requirements():
    script = Path(__file__).parent.parent / "kit-bootstrap.sh"

    with tempfile.TemporaryDirectory() as tmp_dir:
        proj_dir = Path(tmp_dir)

        # Simular arquivos pré-existentes
        env_file = proj_dir / ".env"
        env_file.write_text("MY_SECRET_KEY=supersecret123\nDATABASE_URL=postgres://db\n", encoding="utf-8")

        req_file = proj_dir / "requirements.txt"
        req_file.write_text("django==4.2.0\n", encoding="utf-8")

        # Executar kit-bootstrap com --dry-run no diretório temporário
        result = subprocess.run(
            ["bash", str(script), "--dry-run"],
            capture_output=True,
            text=True,
            cwd=str(proj_dir),
        )
        assert result.returncode == 0
        # Validar que o aviso explícito de salvaguardas foi acionado
        assert "requirements.txt" in result.stdout
        assert ".env" in result.stdout
