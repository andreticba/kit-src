# test_spec_tasks_config.py | Vitalia SDD v0.6.0 | 16-10-2026 16:55(GMT-04:00)
import sys
from pathlib import Path
import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def test_spec_tasks_extension_decoupled():
    toml_path = Path(__file__).parent.parent / "source" / "extensions" / "spec-tasks.toml"
    assert toml_path.exists(), "spec-tasks.toml deve existir em source/extensions/"

    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    # Validar que hooks.after não existe ou está vazio (desacoplamento formal FR-006)
    hooks = data.get("hooks", {})
    after_hooks = hooks.get("after", [])
    assert len(after_hooks) == 0, f"O hook [hooks].after deve estar vazio em spec-tasks.toml, encontrado: {after_hooks}"

    # Validar que o prompt orienta o handoff para /vitalia-task-verifier
    prompt = data.get("prompt") or data.get("transport", {}).get("prompt", "")
    assert "/vitalia-task-verifier" in prompt, "O prompt de spec-tasks deve indicar o handoff formal para /vitalia-task-verifier"
