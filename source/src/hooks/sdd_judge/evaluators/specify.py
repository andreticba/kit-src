# specify.py | Vitalia SDD v0.6.0 | 12-10-2026 21:11(GMT-04:00)
import sys
import re
from typing import Optional
from sdd_judge.evaluators.base import BaseEvaluator
from sdd_judge.prompts.loader import load_prompt_template
from sdd_judge.providers import run_inference_with_failover


class SpecifyEvaluator(BaseEvaluator):
    """Estratégia de auditoria holística integral de requisitos funcionais (spec.md) (FR-001)."""

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

        # Avaliação holística: sem truncamento arbitrário [:4000]
        itens = "\n\n".join(fr_blocks) if fr_blocks else target_content.strip()

        prompt = load_prompt_template(
            "specify",
            feature_name=feature_name,
            rubrica=rubrica,
            itens=itens
        )

        schema = self.load_contract_schema("section_eval_schema.json")
        resp = run_inference_with_failover(prompt, json_schema=schema, task_type="reasoning")
        if not resp or not resp.content:
            print("🚫 VEREDICTO FINAL: BLOCK (Sem resposta da inferência)", file=sys.stderr)
            return 1

        print(f"--- PARECER DO JUIZ [{resp.provider}: {resp.model} | {resp.latency:.2f}s] ---", file=sys.stderr)
        
        parsed = self.parse_structured_evaluation(resp)
        if parsed.get("critique"):
            print(f"Critique: {parsed['critique']}", file=sys.stderr)
        if parsed.get("evidence"):
            print(f"Evidence: {parsed['evidence']}", file=sys.stderr)
        if parsed.get("suggested_fix"):
            print(f"Suggested Fix: {parsed['suggested_fix']}", file=sys.stderr)
        print("----------------------------------------------------------------", file=sys.stderr)

        verdict = parsed.get("verdict", "BLOCK")
        exit_code = parsed.get("exit_code", 1)

        if exit_code == 0:
            print(f"✅ VEREDICTO FINAL: {verdict}", file=sys.stderr)
        else:
            print(f"🚫 VEREDICTO FINAL: {verdict}", file=sys.stderr)
        return exit_code
