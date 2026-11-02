# test_brainstorming_to_route_flow.py | Vitalia SDD v0.6.0 | 18-10-2026 11:35(GMT-04:00)
"""
Teste de integração do fluxo Brainstorming -> Route:
Valida a geração de handoff forward, validação pré-hook no hook runner,
ingestão em session_context.handoff pelo Guardian e consumo atômico.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = REPO_ROOT / "source" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import vitalia_handoff


def test_brainstorming_to_route_complete_flow(tmp_path):
    """
    Testa o fluxo ponta a ponta:
    1. Brainstorming conclui ideação e cria handoff forward apontando para a síntese Markdown.
    2. Hook runner executa com --phase before para vitalia-route e detecta o handoff.
    3. Guardian injeta session_context.handoff com direction="forward".
    4. Handoff é consumido atomicamente pelo dispatcher.
    """
    handoff_dir = REPO_ROOT / ".vitalia" / "memory" / "data_storage" / "handoffs"
    handoff_dir.mkdir(parents=True, exist_ok=True)

    # 1. Criação do handoff forward
    summary_path = "specs/kit-routing-subagents/research-brainstorming.md"
    handoff_file = vitalia_handoff.create_handoff(
        source_workflow="brainstorming",
        target_workflow="route",
        intent_type="brainstorming_to_route",
        source_input="Fluxo de onboarding integrado",
        normalized_summary=summary_path,
        direction="forward",
        detected_domain="design-thinking",
        feature_context="specs/kit-routing-subagents",
        storage_dir=handoff_dir
    )

    try:
        assert handoff_file.exists()
        payload = vitalia_handoff.validate_handoff_file(handoff_file)
        assert payload["envelope"]["direction"] == "forward"
        assert payload["envelope"]["status"] == "pending"

        # 2. Execução do hook runner para vitalia-route
        route_toml = REPO_ROOT / "source" / "extensions" / "route.toml"
        hook_runner_script = SRC_DIR / "vitalia_hook_runner.py"

        cmd = [
            sys.executable,
            str(hook_runner_script),
            str(route_toml),
            "--phase", "before",
            "--args", "confirmar roteamento"
        ]

        env = os.environ.copy()
        env["VITALIA_KIT_DIR"] = str(REPO_ROOT / "source")
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT), env=env)

        assert res.returncode == 0, f"Hook runner falhou: {res.stderr}"
        assert "📦 Handoff validado com sucesso" in res.stderr

        # 3. Validação do stub emitido e do arquivo de contexto físico
        stub = json.loads(res.stdout)
        assert stub.get("status") == "ready"
        context_file = Path(stub["workflow_context_file"])
        assert context_file.exists()

        context_data = json.loads(context_file.read_text(encoding="utf-8"))
        session_ctx = context_data.get("guardian_json", {}).get("session_context", {})

        assert "handoff" in session_ctx, "session_context.handoff não foi injetado pelo Guardian"
        assert session_ctx["handoff"]["envelope"]["direction"] == "forward"
        assert session_ctx["handoff"]["intent"]["normalized_summary"] == summary_path

        # 4. Consumo atômico do handoff
        consumed_payload = vitalia_handoff.consume_handoff(handoff_file)
        assert consumed_payload["envelope"]["status"] == "consumed"

        # Verifica que o arquivo físico está com status consumed
        reloaded = vitalia_handoff.validate_handoff_file(handoff_file)
        assert reloaded["envelope"]["status"] == "consumed"

    finally:
        # Limpeza do arquivo de teste
        if handoff_file.exists():
            handoff_file.unlink()


def test_fallback_level_3_creates_fallback_handoff(tmp_path):
    """
    Testa o fluxo de fallback Nível 3: entrada vaga gera handoff para brainstorming com direction="fallback".
    """
    handoff_dir = REPO_ROOT / ".vitalia" / "memory" / "data_storage" / "handoffs"
    handoff_dir.mkdir(parents=True, exist_ok=True)

    fallback_file = vitalia_handoff.create_handoff(
        source_workflow="vitalia-route",
        target_workflow="brainstorming",
        intent_type="route_to_brainstorming",
        source_input="coisa rápida aí",
        normalized_summary="Intenção vaga não mapeada. Retornando ao brainstorming socrático.",
        direction="fallback",
        detected_domain="",
        feature_context="",
        storage_dir=handoff_dir
    )

    try:
        assert fallback_file.exists()
        payload = vitalia_handoff.validate_handoff_file(fallback_file)
        assert payload["envelope"]["direction"] == "fallback"
        assert payload["routing"]["fallback_used"] is True
    finally:
        if fallback_file.exists():
            fallback_file.unlink()
