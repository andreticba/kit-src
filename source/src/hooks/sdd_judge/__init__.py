# __init__.py | Vitalia SDD v0.6.0 | 16-09-2026 21:00(GMT-04:00)
import sys
from pathlib import Path
from typing import Optional
from unittest.mock import patch

from sdd_judge.evaluators.base import BaseEvaluator
from sdd_judge.evaluators.specify import SpecifyEvaluator
from sdd_judge.evaluators.plan import PlanEvaluator
from sdd_judge.evaluators.tasks import TasksEvaluator
from sdd_judge.evaluators.clarify import ClarifyEvaluator
from sdd_judge.evaluators.converge import ConvergeEvaluator
from sdd_judge.evaluators.after_task import AfterTaskEvaluator
from sdd_judge.providers import run_inference_with_failover

__version__ = "0.6.0"


class SDDJudge:
    """Classe fachada para manter 100% de compatibilidade retroativa com a suíte de testes legada."""

    def __init__(self, mode: Optional[str] = None, target_file: Optional[Path] = None, profile_path: Optional[Path] = None):
        if mode and isinstance(mode, (str, Path)) and not target_file and not profile_path:
            profile_path = Path(mode)
            mode = None

        self.mode = str(mode) if mode else None
        self.target_file = Path(target_file) if target_file else None
        self.profile_path = Path(profile_path) if profile_path else None

    def _get_env_var(self, name: str, default: str) -> str:
        evaluator = SpecifyEvaluator(self.profile_path)
        return evaluator.get_env_var(name, default)

    def _parse_verdict(self, response: str) -> int:
        evaluator = SpecifyEvaluator(self.profile_path)
        return evaluator.parse_verdict(response)

    def _run_inference(self, prompt: str) -> Optional[str]:
        return run_inference_with_failover(prompt)

    def _evaluate_clarify(self, spec_content: str, feature_name: str) -> int:
        evaluator = ClarifyEvaluator(self.profile_path)
        with patch('sdd_judge.evaluators.clarify.run_inference_with_failover', lambda prompt: self._run_inference(prompt)):
            return evaluator.evaluate(spec_content, feature_name)

    def _evaluate_converge(self, spec_content: str, feature_name: str) -> int:
        evaluator = ConvergeEvaluator(self.profile_path)
        with patch('sdd_judge.evaluators.converge.run_inference_with_failover', lambda prompt: self._run_inference(prompt)):
            return evaluator.evaluate(spec_content, feature_name)

    def evaluate(self) -> int:
        if not self.mode:
            print("🚫 [SDDJudge Facade] Erro: Modo não especificado.", file=sys.stderr)
            return 1
        feature_name = self.target_file.parent.name if self.target_file else "Geral"
        target_content = self.target_file.read_text(encoding="utf-8") if self.target_file and self.target_file.exists() else ""

        evaluators = {
            "specify": SpecifyEvaluator,
            "plan": PlanEvaluator,
            "tasks": TasksEvaluator,
            "clarify": ClarifyEvaluator,
            "converge": ConvergeEvaluator,
            "after_task": AfterTaskEvaluator
        }
        cls = evaluators.get(self.mode)
        if not cls:
            return 1
        evaluator = cls(self.profile_path)
        with patch(f'sdd_judge.evaluators.{self.mode}.run_inference_with_failover', lambda prompt: self._run_inference(prompt)):
            return evaluator.evaluate(target_content, feature_name)
