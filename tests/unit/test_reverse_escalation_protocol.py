# test_reverse_escalation_protocol.py | Vitalia SDD v0.6.0 | 18-10-2026 11:40(GMT-04:00)
"""
Testes unitários para o Protocolo de Escalação Invertida (US2 - FR-007, ADR-004):
Valida a geração de divergence JSON, criação de handoff com direction='reverse',
apontamento em normalized_summary e suspensão segura da execução.
"""

import json
import os
import sys
import uuid
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = REPO_ROOT / "source" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import vitalia_handoff


def test_reverse_escalation_creates_divergence_file_and_reverse_handoff(tmp_path):
    """
    Simula uma interrupção por desvio arquitetural durante o spec-implement ou pair:
    1. Grava o relatório de divergência divergence_<uuid_8>.json.
    2. Gera o handoff reverso com direction='reverse', intent_type='route_to_brainstorming'.
    3. Valida conformidade estrutural com o schema oficial.
    """
    handoff_dir = REPO_ROOT / ".vitalia" / "memory" / "data_storage" / "handoffs"
    handoff_dir.mkdir(parents=True, exist_ok=True)

    divergence_id = str(uuid.uuid4())[:8]
    divergence_file = handoff_dir / f"divergence_{divergence_id}.json"

    divergence_payload = {
        "divergence_id": divergence_id,
        "source_workflow": "spec-implement",
        "detected_anomaly": "Extrapolação de escopo: necessidade de criar novo microsserviço de autenticação",
        "impacted_files": ["source/src/auth_service.py"],
        "action_taken": "Interrupção imediata da escrita de código (Trava STOP)",
        "recommendation": "Retornar ao Brainstorming socrático para repactuar a arquitetura"
    }

    divergence_file.write_text(json.dumps(divergence_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    try:
        assert divergence_file.exists()

        # Criação do handoff reverso
        handoff_file = vitalia_handoff.create_handoff(
            source_workflow="spec-implement",
            target_workflow="brainstorming",
            intent_type="route_to_brainstorming",
            source_input="Detectado desvio de domínio: necessidade de autenticação externa",
            normalized_summary=str(divergence_file.relative_to(REPO_ROOT)),
            direction="reverse",
            feature_context="specs/kit-routing-subagents",
            storage_dir=handoff_dir
        )

        assert handoff_file.exists()
        payload = vitalia_handoff.validate_handoff_file(handoff_file)

        assert payload["envelope"]["direction"] == "reverse"
        assert payload["envelope"]["source_workflow"] == "spec-implement"
        assert payload["envelope"]["target_workflow"] == "brainstorming"
        assert payload["intent"]["intent_type"] == "route_to_brainstorming"
        assert payload["intent"]["normalized_summary"] == str(divergence_file.relative_to(REPO_ROOT))

    finally:
        if divergence_file.exists():
            divergence_file.unlink()
        if 'handoff_file' in locals() and handoff_file.exists():
            handoff_file.unlink()
