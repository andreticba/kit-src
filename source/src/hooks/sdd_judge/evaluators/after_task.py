# after_task.py | Vitalia SDD v0.6.0 | 16-09-2026 21:00(GMT-04:00)
import sys
import subprocess
from typing import Optional
from sdd_judge.evaluators.base import BaseEvaluator
from sdd_judge.prompts.loader import load_prompt_template
from sdd_judge.providers import run_inference_with_failover


class AfterTaskEvaluator(BaseEvaluator):
    """Estratégia de auditoria pós-implementação de tarefa (Git Diff)."""

    def _get_git_diff(self) -> str:
        try:
            res = subprocess.run(["git", "diff", "HEAD"], capture_output=True, text=True, check=False)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
            res_cached = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True, check=False)
            if res_cached.returncode == 0 and res_cached.stdout.strip():
                return res_cached.stdout.strip()
        except Exception:
            pass
        return "(Sem diff git detectado)"

    def evaluate(self, target_content: str, feature_name: str) -> int:
        rubrica = self.build_rubric("after_task")
        diff_content = target_content if target_content and "diff --git" in target_content else self._get_git_diff()

        prompt = load_prompt_template(
            "after_task",
            rubrica=rubrica,
            diff_content=diff_content[:15000]
        )

        response = run_inference_with_failover(prompt)
        if not response:
            print("🚫 VEREDICTO FINAL: BLOCK (Sem resposta da inferência)", file=sys.stderr)
            return 1

        print("--- PARECER DO JUIZ (GEMINI API / AFTER_TASK) ---", file=sys.stderr)
        print(response, file=sys.stderr)
        print("-------------------------------------------------", file=sys.stderr)

        code = self.parse_verdict(response)
        if code == 0:
            print("✅ VEREDICTO FINAL: PASS", file=sys.stderr)
        else:
            print("🚫 VEREDICTO FINAL: BLOCK", file=sys.stderr)
        return code
