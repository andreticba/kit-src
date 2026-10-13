# base.py | Vitalia SDD v0.6.0 | 12-10-2026 21:11(GMT-04:00)
import os
import sys
import json
import re
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any, Union
from sdd_judge.providers.base import LLMResponse

try:
    import yaml
    _YAML_OK = True
except ImportError:
    _YAML_OK = False


class BaseEvaluator(ABC):
    """Classe base abstrata para todas as estratégias de auditoria por fase com suporte a Structured Outputs."""

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

    def load_contract_schema(self, schema_name: str) -> Dict[str, Any]:
        """Carrega um arquivo JSON Schema da pasta de contratos oficial."""
        base_dir = Path(__file__).resolve().parent.parent / "contracts"
        schema_file = base_dir / schema_name
        if not schema_file.exists():
            # Fallback para spec local se em desenvolvimento
            dev_file = Path.cwd() / "specs" / "sdd-judge-robustness" / "contracts" / schema_name
            if dev_file.exists():
                schema_file = dev_file
        try:
            with open(schema_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[SDDJudge] ⚠️ Erro ao carregar contrato {schema_name}: {e}", file=sys.stderr)
            return {}

    def parse_structured_evaluation(self, response: Union[LLMResponse, str]) -> Dict[str, Any]:
        """Processa a resposta do modelo aplicando o contrato de JSON Schema e governança graduada de WARN (FR-002 e FR-003)."""
        content_str = response.content if isinstance(response, LLMResponse) else str(response)
        provider = response.provider if isinstance(response, LLMResponse) else "Desconhecido"
        model = response.model if isinstance(response, LLMResponse) else "Desconhecido"
        latency = response.latency if isinstance(response, LLMResponse) else 0.0

        default_result: Dict[str, Any] = {
            "critique": "",
            "evidence": "",
            "verdict": "BLOCK",
            "warn_severity": "EXTREME",
            "suggested_fix": "",
            "exit_code": 1,
            "provider": provider,
            "model": model,
            "latency": latency,
            "raw": content_str
        }

        if not content_str or not content_str.strip():
            default_result["critique"] = "Resposta vazia recebida do avaliador."
            return default_result

        # Limpeza de markdown envoltório
        clean_text = re.sub(r'```(?:json)?\s*', '', content_str, flags=re.IGNORECASE)
        clean_text = re.sub(r'\s*```', '', clean_text).strip()

        data: Dict[str, Any] = {}
        try:
            data = json.loads(clean_text)
        except Exception:
            # Fallback de extração de bloco JSON por regex se houver texto espúrio
            match = re.search(r'(\{[\s\S]*\})', clean_text)
            if match:
                try:
                    data = json.loads(match.group(1))
                except Exception:
                    pass

        if not data or not isinstance(data, dict):
            # Fallback para parsing clássico por regex caso constrained decoding falhe
            if re.search(r'VEREDICTO_FINAL[\s\*:[\]]+PASS\b', content_str, re.IGNORECASE):
                default_result["verdict"] = "PASS"
                default_result["warn_severity"] = "NONE"
                default_result["exit_code"] = 0
            elif re.search(r'VEREDICTO_FINAL[\s\*:[\]]+WARN\b', content_str, re.IGNORECASE):
                default_result["verdict"] = "WARN"
                default_result["warn_severity"] = "LOW"
                default_result["exit_code"] = 0
            return default_result

        critique = str(data.get("critique", "")).strip()
        evidence = str(data.get("evidence", "")).strip()
        verdict = str(data.get("verdict", "BLOCK")).upper().strip()
        warn_severity = str(data.get("warn_severity", "NONE")).upper().strip()
        suggested_fix = str(data.get("suggested_fix", "")).strip()

        # Governança de severidade de avisos (FR-003):
        # - PASS -> exit_code 0
        # - WARN LOW / MEDIUM / NONE -> exit_code 0
        # - WARN EXTREME -> elevado para BLOCK programático (exit_code 1)
        # - BLOCK -> exit_code 1
        exit_code = 0
        if verdict == "PASS":
            exit_code = 0
        elif verdict == "WARN":
            if warn_severity == "EXTREME":
                exit_code = 1
                verdict = "WARN (EXTREME -> BLOCK)"
            else:
                exit_code = 0
        else:
            exit_code = 1

        return {
            "critique": critique,
            "evidence": evidence,
            "verdict": verdict,
            "warn_severity": warn_severity,
            "suggested_fix": suggested_fix,
            "exit_code": exit_code,
            "provider": provider,
            "model": model,
            "latency": latency,
            "raw": content_str
        }

    def parse_verdict(self, response: Union[LLMResponse, str]) -> int:
        parsed = self.parse_structured_evaluation(response)
        return parsed.get("exit_code", 1)

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
