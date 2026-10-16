# test_task_verifier_lifecycle.py | Vitalia SDD v0.6.0 | 16-10-2026 16:55(GMT-04:00)
import os
import subprocess
import tempfile
from pathlib import Path
import pytest


def test_task_verifier_lifecycle_simulation():
    repo_root = Path(__file__).parent.parent
    extension_file = repo_root / "source" / "extensions" / "task-verifier.toml"
    assert extension_file.exists()

    with tempfile.TemporaryDirectory() as tmp_dir:
        feature_dir = Path(tmp_dir) / "specs" / "test-feature"
        feature_dir.mkdir(parents=True)

        tasks_file = feature_dir / "tasks.md"
        tasks_file.write_text(
            "# Tasks: Test Feature\n- [ ] T001 [P] Setup inicial em path/to/file.py\n",
            encoding="utf-8",
        )

        # 1. Validar que antes da aprovação, tasks.md.bak não existe e carimbo está ausente
        backup_file = feature_dir / "tasks.md.bak"
        assert not backup_file.exists()
        assert "constitutional-status: APPROVED" not in tasks_file.read_text(encoding="utf-8")

        # 2. Simular geração do Relatório de inspeção
        report_file = feature_dir / "Relatório de inspeção.md"
        report_file.write_text(
            "# Relatório de Inspeção Constitucional: test-feature\n## Resumo: 1 Conforme\n",
            encoding="utf-8",
        )
        assert report_file.exists()

        # 3. Simular aprovação soberana HITL: criação de backup e carimbo constitucional
        backup_file.write_text(tasks_file.read_text(encoding="utf-8"), encoding="utf-8")
        assert backup_file.exists()

        stamped_content = (
            "<!-- constitutional-status: APPROVED | auditor: red-team-vitalia | timestamp: 2026-10-16T16:55:00-04:00 | report: Relatório de inspeção.md -->\n"
            + tasks_file.read_text(encoding="utf-8")
        )
        tasks_file.write_text(stamped_content, encoding="utf-8")

        assert "constitutional-status: APPROVED" in tasks_file.read_text(encoding="utf-8")
        assert backup_file.exists()
