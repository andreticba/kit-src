# base.py | Vitalia SDD v0.6.0 | 16-09-2026 21:00(GMT-04:00)
import os
import sys
import json
import re
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

try:
    import yaml
    _YAML_OK = True
except ImportError:
    _YAML_OK = False


class BaseEvaluator(ABC):
    """Classe base abstrata para todas as estratégias de auditoria por fase."""

    def __init__(self, profile_path: Optional[Path] = None):
        if profile_path and isinstance(profile_path, str):
            profile_path = Path(profile_path)
        self.profile_path = profile_path or self._resolve_profile_path()
        self.profile_data = self._load_profile()

    def _resolve_profile_path(self) -> Path:
        return Path.home() / ".vitalia" / "profiles" / "gp_sdd-judge.yaml"

    def _load_profile(self) -> Dict:
        if not self.profile_path.exists():
            print(f"[SDDJudge] ⚠️ Perfil não encontrado em: {self.profile_path}", file=sys.stderr)
            return {}
        if not _YAML_OK:
            print("[SDDJudge] ⚠️ PyYAML não instalado.", file=sys.stderr)
            return {}
        try:
            with open(self.profile_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"[SDDJudge] ⚠️ Erro ao ler perfil {self.profile_path}: {e}", file=sys.stderr)
            return {}

    def get_env_var(self, name: str, default: str) -> str:
        return os.environ.get(name, default).strip()

    def parse_verdict(self, response: str) -> int:
        if not response or not response.strip():
            return 1
        response_clean = re.sub(r'```(?:json)?\s*', '', response, flags=re.IGNORECASE)
        response_clean = re.sub(r'\s*```', '', response_clean).strip()
        try:
            data = json.loads(response_clean)
            if isinstance(data, dict) and "verdict" in data:
                return 0 if str(data["verdict"]).upper() == "PASS" else 1
        except (json.JSONDecodeError, TypeError):
            pass

        if re.search(r'VEREDICTO_FINAL[\s\*:[\]]+PASS\b', response, re.IGNORECASE):
            return 0
        if re.search(r'VEREDICTO_FINAL[\s\*:[\]]+WARN\b', response, re.IGNORECASE):
            return 0
        return 1

    def build_rubric(self, mode: str) -> str:
        phase_profiles = self.profile_data.get("phase_profiles", {})
        phase_cfg = phase_profiles.get(mode, {})
        principles_include = phase_cfg.get("principles_include", [])

        constitution_data = self._load_constitution()
        if not constitution_data:
            return "(Rubrica base de fallback: P01, P02, P03)"

        principles = constitution_data.get("principles", {})
        lines = []
        for code in principles_include:
            p = principles.get(code, {})
            if p:
                lines.append(f"- [{code}] {p.get('name', '')} ({p.get('severity', 'WARNING')}): {p.get('rule', '').strip()}")

        return "\n".join(lines) if lines else "(Rubrica sem princípios mapeados)"

    def _load_constitution(self) -> Dict:
        const_path = Path.home() / ".vitalia" / "profiles" / "constitution.yaml"
        if not const_path.exists() or not _YAML_OK:
            return {}
        try:
            with open(const_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    @abstractmethod
    def evaluate(self, target_content: str, feature_name: str) -> int:
        """Executa a auditoria da fase e retorna exit code (0 para PASS/WARN, 1 para BLOCK)."""
        pass
