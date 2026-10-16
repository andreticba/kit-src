# test_task_verifier_context.py | Vitalia SDD v0.6.0 | 16-10-2026 16:55(GMT-04:00)
import sys
from pathlib import Path
import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def test_task_verifier_extension_specification():
    toml_path = Path(__file__).parent.parent / "source" / "extensions" / "task-verifier.toml"
    assert toml_path.exists(), "task-verifier.toml deve existir em source/extensions/"

    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    # Validar Context Lifting no Guardian (§11)
    guardian = data.get("guardian", {})
    assert "constitution" in guardian.get("yaml_sources", []), "yaml_sources deve conter 'constitution'"

    # Validar ausência de hooks externos quebrados
    hooks = data.get("hooks", {})
    assert "sdd_judge.py --mode tasks" not in str(hooks.get("before", []))
    assert "sdd_judge.py --mode tasks" not in str(hooks.get("after", []))

    # Validar o prompt do Red Team
    prompt = guardian.get("prompt", "") or data.get("prompt", "")
    assert "Red Team" in prompt, "O prompt deve estabelecer a persona Red Team Constitucional"
    assert "Relatório de inspeção.md" in prompt, "O prompt deve exigir a geração de specs/{feature}/Relatório de inspeção.md"
    assert "chat" in prompt.lower(), "O prompt deve exigir confirmação explícita no chat antes da aprovação"
    assert "tasks.md.bak" in prompt, "O prompt deve exigir a criação de tasks.md.bak"
    assert "constitutional-status: APPROVED" in prompt, "O prompt deve especificar a gravação do carimbo constitucional"
    assert "FEW-SHOT" in prompt.upper(), "O prompt deve conter blocos de Few-Shot Prompting para exemplificar a auditoria"
    assert "- **P01 (SDD Pipeline)" not in prompt, "O prompt não deve conter lista hardcoded de princípios constitucionais"
