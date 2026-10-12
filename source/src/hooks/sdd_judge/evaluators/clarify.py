# clarify.py | Vitalia SDD v0.6.0 | 16-09-2026 21:00(GMT-04:00)
import sys
import json
import re
from typing import Optional
from sdd_judge.evaluators.base import BaseEvaluator
from sdd_judge.prompts.loader import load_prompt_template
from sdd_judge.providers import run_inference_with_failover


class ClarifyEvaluator(BaseEvaluator):
    """Estratégia de auditoria de ambiguidades taxonômicas (spec.md) conforme ISO 29148."""

    def evaluate(self, target_content: str, feature_name: str) -> int:
        prompt = load_prompt_template(
            "clarify",
            feature_name=feature_name,
            spec_content=target_content[:15000]
        )

        response = run_inference_with_failover(prompt)
        if not response:
            print("🚫 VEREDICTO FINAL: BLOCK (Sem resposta da inferência)", file=sys.stderr)
            return 1

        print("--- PARECER DO JUIZ (GEMINI API / CLARIFY) ---", file=sys.stderr)
        print(response, file=sys.stderr)
        print("---------------------------------------------", file=sys.stderr)

        code = self.parse_verdict(response)
        if code == 0:
            print("✅ VEREDICTO FINAL: PASS (Sem ambiguidades impeditivas)", file=sys.stderr)
        else:
            print("🚫 VEREDICTO FINAL: BLOCK (Ambiguidades críticas detectadas)", file=sys.stderr)
        return code
