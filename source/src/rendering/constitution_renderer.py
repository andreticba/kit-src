#!/usr/bin/env python3
# constitution_renderer.py | Vitalia Kit — Domínio RENDERING
# Atualizado em: 28-08-2026 09:00:00(GMT-04:00)
"""
Compilador Visual da Constituição — Vitalia Kit (Domínio RENDERING)

Responsabilidades:
1. Ler constitution_data.yaml e compilar para architect-constitution.md.
2. Renderizar seções expansíveis (<details><summary>), badges Shields.io e topologia Mermaid.
3. Atender ao padrão visual rico de documentação do Vitalia Kit.
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Any

_scripts_root = str(Path(__file__).resolve().parent.parent)
if _scripts_root not in sys.path:
    sys.path.insert(0, _scripts_root)

import kit_env_bootstrap
health = kit_env_bootstrap.init()
from core.utils import get_timestamp, format_visible_header


class ConstitutionRenderer:
    def __init__(self, kit_root: Path):
        self.kit_root = kit_root
        self.yaml_file = kit_root / "profiles" / "constitution.yaml"
        self.output_md = kit_root / "docs" / "constitution_rendered.md"

    def compile(self) -> Path:
        if not self.yaml_file.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {self.yaml_file}")

        data = yaml.safe_load(self.yaml_file.read_text(encoding="utf-8"))
        modules = data.get("modules", [])

        lines = [
            f"<!-- architect-constitution.md | Compilado em: {get_timestamp()} -->",
            "# 📜 Constituição de Arquitetura, Segurança e Governança Vitalia",
            "",
            "<div align='center'>",
            "",
            "![Status](https://img.shields.io/badge/Constituição-ATIVA-brightgreen?style=for-the-badge)",
            f"![Versão](https://img.shields.io/badge/Versão-{data.get('schema_version', '0.5.0')}-purple?style=for-the-badge)",
            "![Enforcement](https://img.shields.io/badge/Enforcement-TASK_VERIFIER-blue?style=for-the-badge)",
            "",
            "</div>",
            "",
            format_visible_header(),
            "",
            "> ⚠️ **DOCUMENTO GERADO DETERMINISTICAMENTE:** Não edite este arquivo diretamente. Edite `constitution_data.yaml`.",
            "",
            "---",
            "",
            "## 🗺️ Mapa de Governança Constitucional",
            "",
            "<div align='center'>",
            "",
            "```mermaid",
            "flowchart TD",
            "  C((\"Constituicao Vitalia\"))"
        ]

        for mod in modules:
            m_id = mod.get("id", "MOD")
            m_name = mod.get("name", "Módulo")
            lines.append(f'  C --> M_{m_id}["📦 {m_name}"]')
            for p in mod.get("principles", []):
                p_id = p.get("id", "P")
                p_name = p.get("name", "Princípio")
                lines.append(f'  M_{m_id} --> P_{p_id}["⚡ {p_id}: {p_name}"]')

        lines.extend([
            "```",
            "",
            "</div>",
            "",
            "---",
            "",
            "## 📑 Módulos Constitucionais e Regras Invioláveis",
            ""
        ])

        for mod in modules:
            m_name = mod.get("name", "Módulo")
            m_desc = mod.get("description", "")
            lines.append("<details>")
            lines.append(f"<summary><h3>📦 {m_name}</h3></summary>")
            lines.append("")
            lines.append(f"> _{m_desc}_")
            lines.append("")
            lines.append("| ID | Princípio | Nível | Severidade | Regra | Validador |")
            lines.append("|---|---|---|---|---|---|")
            for p in mod.get("principles", []):
                p_id = p.get("id", "P")
                p_name = p.get("name", "Princípio")
                p_lvl = p.get("level", "MUST")
                p_sev = p.get("severity", "BLOCKING")
                p_rule = p.get("rule", "").replace("|", "-")
                p_val = p.get("validator", "")
                lines.append(f"| `{p_id}` | **{p_name}** | `{p_lvl}` | `{p_sev}` | {p_rule} | `{p_val}` |")
            lines.append("")
            lines.append("</details>")
            lines.append("")

        self.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return self.output_md


def main():
    kit_root = Path.home() / ".vitalia"
    renderer = ConstitutionRenderer(kit_root)
    out = renderer.compile()
    print(f"✅ architect-constitution.md compilado com sucesso em: {out}")


if __name__ == "__main__":
    main()
