# converge.py | Vitalia SDD v0.6.0 | 16-09-2026 21:00(GMT-04:00)
import sys
from pathlib import Path
from typing import Optional
from sdd_judge.evaluators.base import BaseEvaluator
from sdd_judge.prompts.loader import load_prompt_template
from sdd_judge.providers import run_inference_with_failover


class ConvergeEvaluator(BaseEvaluator):
    """Estratégia de reconciliação semântica cruzada spec x plan x tasks x código."""

    def evaluate(self, target_content: str, feature_name: str) -> int:
        feature_dir = Path(target_content).parent if isinstance(target_content, (str, Path)) and Path(target_content).exists() else None
        tasks_content = ""
        spec_content = target_content

        if feature_dir:
            spec_file = feature_dir / "spec.md"
            tasks_file = feature_dir / "tasks.md"
            if spec_file.exists():
                spec_content = spec_file.read_text(encoding="utf-8")
            if tasks_file.exists():
                tasks_content = tasks_file.read_text(encoding="utf-8")

        prompt = load_prompt_template(
            "converge",
            feature_name=feature_name,
            spec_content=spec_content[:10000],
            tasks_content=tasks_content[:10000]
        )

        response = run_inference_with_failover(prompt)
        if not response:
            print("🚫 VEREDICTO FINAL: BLOCK (Sem resposta da inferência)", file=sys.stderr)
            return 1

        print("--- PARECER DO JUIZ (GEMINI API / CONVERGE) ---", file=sys.stderr)
        print(response, file=sys.stderr)
        print("-----------------------------------------------", file=sys.stderr)

        code = self.parse_verdict(response)
        if code == 0:
            print("✅ VEREDICTO FINAL: PASS", file=sys.stderr)
        else:
            print("🚫 VEREDICTO FINAL: BLOCK", file=sys.stderr)
        return code
