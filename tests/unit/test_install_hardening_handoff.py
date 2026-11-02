# test_install_hardening_handoff.py | Vitalia SDD v0.6.0 | 31-10-2026
"""
Suíte de testes de regressão (TDD Red Phase) para Kit Install Hardening:
Valida isolamento de memória, resolução de raiz de projeto, validação estrita
de data_storage, guardrail Zero Data Leak e flag CLI --project-root.
Referência: FR-001 a FR-005, P05, P06.
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

# O teste valida o código em source/src assegurando compatibilidade com a instalação em ~/.vitalia
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = REPO_ROOT / "source" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def test_resolve_project_root_subfolder(tmp_path):
    """Garante resolução da raiz a partir de subpasta profunda sem marcadores (FR-001)."""
    proj = tmp_path / "my_project"
    sub = proj / "src" / "deep" / "nested"
    sub.mkdir(parents=True)
    vit = proj / ".vitalia" / "memory"
    vit.mkdir(parents=True)

    import vitalia_handoff
    resolved = vitalia_handoff.resolve_project_root(start=sub)
    assert resolved == proj


def test_resolve_project_root_from_inside_dot_vitalia_or_data_storage(tmp_path):
    """Garante que start dentro de .vitalia/memory/data_storage sobe para fora da árvore (FR-001)."""
    proj = tmp_path / "my_project"
    ds = proj / ".vitalia" / "memory" / "data_storage" / "handoffs"
    ds.mkdir(parents=True)
    (proj / ".vitalia" / "feature.json").write_text("{}", encoding="utf-8")

    import vitalia_handoff
    resolved = vitalia_handoff.resolve_project_root(start=ds)
    assert resolved == proj


def test_resolve_project_root_rejects_home_and_kit_dir(tmp_path, monkeypatch):
    """Garante que $HOME e ~/.vitalia nunca são aceitos como raiz de projeto (FR-001)."""
    fake_home = tmp_path / "fake_home"
    kit_dir = fake_home / ".vitalia"
    kit_dir.mkdir(parents=True)
    (kit_dir / "memory").mkdir()

    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("VITALIA_KIT_DIR", str(kit_dir))

    import vitalia_handoff
    with pytest.raises(RuntimeError) as exc_info:
        vitalia_handoff.resolve_project_root(start=kit_dir)
    assert "install-project" in str(exc_info.value)

    with pytest.raises(RuntimeError) as exc_info:
        vitalia_handoff.resolve_project_root(start=fake_home)
    assert "install-project" in str(exc_info.value)


def test_resolve_storage_dir_missing_data_storage(tmp_path):
    """Garante erro estrito e retorno None em modo lenient se data_storage estiver ausente (FR-002)."""
    proj = tmp_path / "my_project"
    (proj / ".vitalia").mkdir(parents=True)
    (proj / ".vitalia" / "config.yml").write_text("domain: software", encoding="utf-8")

    import vitalia_handoff
    # Strict mode: lança RuntimeError mencionando install-project e data_storage
    with pytest.raises(RuntimeError) as exc_info:
        vitalia_handoff.resolve_storage_dir(start=proj, lenient=False)
    assert "install-project" in str(exc_info.value)
    assert "data_storage" in str(exc_info.value)

    # Lenient mode: retorna None sem exceção
    assert vitalia_handoff.resolve_storage_dir(start=proj, lenient=True) is None


def test_resolve_storage_dir_guardrail_zero_data_leak(tmp_path, monkeypatch):
    """Garante que o guardrail final Zero Data Leak bloqueia caminhos sob ~/.vitalia ou $HOME (FR-003)."""
    fake_home = tmp_path / "fake_home"
    kit_dir = fake_home / ".vitalia"
    (kit_dir / "memory" / "data_storage" / "handoffs").mkdir(parents=True)

    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("VITALIA_KIT_DIR", str(kit_dir))

    import vitalia_handoff
    with pytest.raises(RuntimeError) as exc_info:
        vitalia_handoff.resolve_storage_dir(start=kit_dir, lenient=False)
    assert "install-project" in str(exc_info.value) or "Zero Data Leak" in str(exc_info.value)


def test_cli_project_root_flag(tmp_path):
    """Garante que a flag --project-root nos subcomandos CLI opera deterministicamente (FR-004)."""
    proj = tmp_path / "my_proj"
    ds = proj / ".vitalia" / "memory" / "data_storage"
    ds.mkdir(parents=True)
    (proj / ".vitalia" / "feature.json").write_text("{}", encoding="utf-8")

    cmd_create = [
        sys.executable,
        str(SRC_DIR / "vitalia_handoff.py"),
        "create",
        "--project-root", str(proj),
        "--source", "brainstorming",
        "--target", "vitalia-route",
        "--direction", "forward",
        "--intent", "brainstorming_to_route",
        "--input", "Teste CLI --project-root",
        "--summary", "specs/test.md"
    ]
    res = subprocess.run(cmd_create, capture_output=True, text=True, cwd=str(tmp_path))
    assert res.returncode == 0, f"Stderr: {res.stderr}"
    data = json.loads(res.stdout)
    assert str(proj) in data["file"]

    cmd_latest = [
        sys.executable,
        str(SRC_DIR / "vitalia_handoff.py"),
        "latest",
        "--project-root", str(proj),
        "--target", "vitalia-route"
    ]
    res_latest = subprocess.run(cmd_latest, capture_output=True, text=True, cwd=str(tmp_path))
    assert res_latest.returncode == 0
    assert str(proj) in res_latest.stdout
