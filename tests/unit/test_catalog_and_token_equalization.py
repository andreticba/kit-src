# test_catalog_and_token_equalization.py | Vitalia SDD v0.6.0 | 20-10-2026 09:50(GMT-04:00)
"""
Testes unitários para validação do catálogo de agentes saneado (FR-008, FR-009),
equalização adaptativa de tokens no Guardian (FR-011) e regex do instalador (FR-010).
"""

import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
import jsonschema
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = REPO_ROOT / "source" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

CATALOG_PATH = REPO_ROOT / "source" / "profiles" / "agents_catalog.yaml"
SCHEMA_PATH = REPO_ROOT / "source" / "config" / "schemas" / "agents_catalog.schema.json"


@pytest.fixture
def catalog_data():
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def catalog_schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_agents_catalog_validates_against_schema(catalog_data, catalog_schema):
    """Garante que o catálogo saneado é 100% válido contra o schema JSON."""
    jsonschema.validate(instance=catalog_data, schema=catalog_schema)


def test_agents_catalog_statuses_and_ai_control_team(catalog_data):
    """Valida status active/planned e presença exclusiva dos 6 especialistas do AI-Control (FR-008, FR-009)."""
    agents = catalog_data.get("agents", [])
    assert len(agents) >= 11

    by_id = {a["id"]: a for a in agents}

    # Único ativo no Kit atual (possui extensão .toml real)
    assert by_id["medical-gate"]["status"] == "active"

    # Planejados no Kit (sem extensão .toml executável no momento)
    assert by_id["design-thinking"]["status"] == "planned"
    assert by_id["literature-curator"]["status"] == "planned"
    assert by_id["visual-creator"]["status"] == "planned"
    assert by_id["architect"]["status"] == "planned"

    # 6 Especialistas oficiais do ecossistema AI-Control (FR-009)
    ai_control_specialists = [
        "master-ai-control",
        "django-stark",
        "react-vinci",
        "infra-nomad",
        "cortex-analyst",
        "figma-maestro"
    ]

    for spec_id in ai_control_specialists:
        assert spec_id in by_id, f"Especialista AI-Control '{spec_id}' não cadastrado no catálogo"
        agent = by_id[spec_id]
        assert agent["status"] == "planned", f"Agente '{spec_id}' deveria ser 'planned'"
        assert agent["command"].startswith("/vitalia-")
        assert len(agent["role"]) > 5

    # Garante que nenhum perfil clínico alucinado sobrou no catálogo base
    clinical_hallucinations = [
        "clinical-researcher",
        "epidemiologist",
        "data-privacy-officer",
        "security-auditor",
        "fhir-integrator",
        "health-economics-analyst"
    ]
    for ch in clinical_hallucinations:
        assert ch not in by_id, f"Perfil clínico alucinado '{ch}' não deveria estar no catálogo base"


def test_guardian_token_equalization_by_hardware_profile():
    """Valida a equalização adaptativa de tokens (lightweight <= 1000, frontier <= 4000)."""
    from hooks.guardian_context import GuardianContextV2

    # Perfil lightweight
    g_light = GuardianContextV2(
        workflow_name="vitalia-route",
        guardian_config={"hardware_profile": "lightweight"},
        cwd=REPO_ROOT
    )
    payload_light = g_light.build_payload()
    assert payload_light["token_budget"] <= 1000

    # Perfil frontier
    g_front = GuardianContextV2(
        workflow_name="brainstorming",
        guardian_config={"hardware_profile": "frontier"},
        cwd=REPO_ROOT
    )
    payload_front = g_front.build_payload()
    assert payload_front["token_budget"] <= 4000


def test_installer_sed_regex_prevents_vitalia_vitalia_duplication():
    """Valida que a regex sed recursiva 's/^(vitalia-)+//' previne prefixos duplicados até em entradas corrompidas."""
    test_cases = [
        ("vitalia-route.toml", "vitalia-route"),
        ("vitalia-integrative-review.toml", "vitalia-integrative-review"),
        ("vitalia-vitalia-route.toml", "vitalia-route"),
        ("vitalia-vitalia-integrative-review.toml", "vitalia-integrative-review"),
        ("brainstorming.toml", "vitalia-brainstorming"),
        ("spec-implement.toml", "vitalia-spec-implement"),
    ]

    for filename, expected_skill in test_cases:
        cmd = f"basename '{filename}' .toml | sed -E 's/^(vitalia-)+//'"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        raw_name = res.stdout.strip()
        skill_name = f"vitalia-{raw_name}"
        assert skill_name == expected_skill
        assert not skill_name.startswith("vitalia-vitalia-")
