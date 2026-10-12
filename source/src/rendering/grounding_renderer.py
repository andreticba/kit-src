#!/usr/bin/env python3
# grounding_renderer.py | Vitalia Kit — Domínio RENDERING
# Atualizado em: 28-08-2026 09:00:00(GMT-04:00)
"""
Compilador de Domínios de Grounding — Vitalia Kit (Domínio RENDERING)
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any

_scripts_root = str(Path(__file__).resolve().parent.parent)
if _scripts_root not in sys.path:
    sys.path.insert(0, _scripts_root)

import kit_env_bootstrap
health = kit_env_bootstrap.init()
from core.utils import get_timestamp, read_jsonl


class GroundingRenderer:
    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.global_domains_file = Path.home() / ".vitalia" / "config" / "grounding-domains.yaml"
        self.local_domains_jsonl = session_dir / "data" / "grounding-domains.jsonl"
        self.output_yaml = session_dir / "grounding-domains-local.yaml"

    def compile(self) -> int:
        pending_count = 0
        local_records = read_jsonl(self.local_domains_jsonl) if self.local_domains_jsonl.exists() else []

        lines = [
            f"# grounding-domains-local.yaml | Compilado em: {get_timestamp()}",
            "# Dicionário de domínios com verificação externa obrigatória",
            "version: '0.5.0'",
            "domains:"
        ]

        canonical_domains = [
            ("llm_models", "modelos, precos, benchmarks LLM"),
            ("python_packages", "versoes e compatibilidade pypi"),
            ("external_apis", "endpoints e contratos de APIs externas"),
            ("security_practices", "vulnerabilidades, CVEs e OWASP"),
            ("regulations", "LGPD, HIPAA, GDPR e conformidade"),
            ("cloud_services", "precos e SLAs de cloud"),
            ("scientific_claims", "artigos, dosagens e referencias medicas")
        ]
        for name, desc in canonical_domains:
            lines.append(f"  - name: '{name}'")
            lines.append(f"    description: '{desc}'")
            lines.append("    scope: 'global'")

        for r in local_records:
            status = r.get("status", "PENDING")
            if status == "PENDING":
                pending_count += 1
            lines.append(f"  - name: '{r.get('domain', '')}'")
            lines.append(f"    description: '{r.get('description', '')}'")
            lines.append("    scope: 'local'")
            lines.append(f"    status: '{status}'")

        self.output_yaml.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return pending_count
