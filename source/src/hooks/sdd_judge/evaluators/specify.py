# specify.py | Vitalia SDD v0.6.0 | 16-09-2026 21:00(GMT-04:00)
import sys
import re
from typing import Optional
from sdd_judge.evaluators.base import BaseEvaluator
from sdd_judge.prompts.loader import load_prompt_template
from sdd_judge.providers import run_inference_with_failover


class SpecifyEvaluator(BaseEvaluator):
    """Estratégia de auditoria constitucional de requisitos funcionais (spec.md)."""

    def evaluate(self, target_content: str, feature_name: str) -> int:
        rubrica = self.build_rubric("specify")
        pattern = self.profile_data.get("phase_profiles", {}).get("specify", {}).get("extraction_pattern", r"^\s*(?:#{1,4}\s*)?-?\s*\*?\*?FR-\d+")

        fr_blocks = []
        current_block = []
        in_fr = False

        for line in target_content.splitlines():
            if re.search(pattern, line):
                if current_block:
                    fr_blocks.append("\n".join(current_block).strip())
                    current_block = []
                in_fr = True
                current_block.append(line)
            elif in_fr:
                if re.match(r"^\s*##\s+", line):
                    in_fr = False
                    if current_block:
                        fr_blocks.append("\n".join(current_block).strip())
                        current_block = []
                else:
                    current_block.append(line)

        if current_block:
            fr_blocks.append("\n".join(current_block).strip())

        itens = "\n\n".join(fr_blocks) if fr_blocks else target_content[:4000]

        prompt = load_prompt_template(
            "specify",
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
