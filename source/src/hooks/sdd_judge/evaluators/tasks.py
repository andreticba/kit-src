# tasks.py | Vitalia SDD v0.6.0 | 16-09-2026 21:00(GMT-04:00)
import sys
import re
from typing import Optional
from sdd_judge.evaluators.base import BaseEvaluator
from sdd_judge.prompts.loader import load_prompt_template
from sdd_judge.providers import run_inference_with_failover


class TasksEvaluator(BaseEvaluator):
    """Estratégia de auditoria constitucional das tarefas atômicas (tasks.md)."""

    def evaluate(self, target_content: str, feature_name: str) -> int:
        rubrica = self.build_rubric("tasks")
        pattern = self.profile_data.get("phase_profiles", {}).get("tasks", {}).get("extraction_pattern", r"^\s*(?:#{1,4}\s*)?-?\s*(?:\[[ xX/\]]\s*)?T\d+")

        task_lines = []
        for line in target_content.splitlines():
            if re.search(pattern, line):
                task_lines.append(line.strip())

        itens = "\n".join(task_lines) if task_lines else target_content[:15000]

        prompt = load_prompt_template(
            "tasks",
            feature_name=feature_name,
            rubrica=rubrica,
            itens=itens
        )

        response = run_inference_with_failover(prompt)
        if not response:
            print("🚫 VEREDICTO FINAL: BLOCK (Sem resposta da inferência)", file=sys.stderr)
            return 1

        print("--- PARECER DO JUIZ (GEMINI API) ---", file=sys.stderr)
        print(response, file=sys.stderr)
        print("------------------------------------", file=sys.stderr)

        code = self.parse_verdict(response)
        if code == 0:
            print("✅ VEREDICTO FINAL: PASS", file=sys.stderr)
        else:
            print("🚫 VEREDICTO FINAL: BLOCK", file=sys.stderr)
        return code
