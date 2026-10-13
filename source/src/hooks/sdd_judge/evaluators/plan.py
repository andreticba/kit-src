# plan.py | Vitalia SDD v0.6.0 | 12-10-2026 21:11(GMT-04:00)
import sys
import re
from typing import Optional, List, Tuple
from sdd_judge.evaluators.base import BaseEvaluator
from sdd_judge.prompts.loader import load_prompt_template
from sdd_judge.providers import run_inference_with_failover


class PlanEvaluator(BaseEvaluator):
    """Estratégia de auditoria constitucional do plano técnico e ADRs por particionamento semântico (plan.md) (FR-001)."""

    def _split_sections(self, content: str) -> List[Tuple[str, str]]:
        """Divide o documento markdown em seções com base nos cabeçalhos ## preservando título e corpo."""
        lines = content.splitlines()
        header_lines = []
        sections = []
        current_title = "Header"
        current_lines = []

        for line in lines:
            if re.match(r"^##\s+", line):
                if current_lines:
                    sections.append((current_title, "\n".join(current_lines).strip()))
                    current_lines = []
                current_title = line.strip()
            current_lines.append(line)

        if current_lines:
            sections.append((current_title, "\n".join(current_lines).strip()))

        return sections

    def evaluate(self, target_content: str, feature_name: str) -> int:
        rubrica = self.build_rubric("plan")
        schema = self.load_contract_schema("section_eval_schema.json")

        sections = self._split_sections(target_content)
        # Se o plano for moderado (< 8000 caracteres), avalia integralmente
        if len(target_content) <= 8000 or len(sections) <= 2:
            prompt = load_prompt_template(
                "plan",
                feature_name=feature_name,
                rubrica=rubrica,
                itens="Documento Completo",
                contexto_plan=target_content
            )
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
            print(f"{'✅' if exit_code == 0 else '🚫'} VEREDICTO FINAL: {verdict}", file=sys.stderr)
            return exit_code

        # Para planos longos: Section Chunking sem corte de 15k
        print(f"[SDDJudge] 📑 Plano extenso ({len(target_content)} chars). Auditando por {len(sections)} seções estruturais...", file=sys.stderr)
        overall_exit_code = 0
        overall_verdict = "PASS"

        for title, section_content in sections:
            prompt = load_prompt_template(
                "plan",
                feature_name=feature_name,
                rubrica=rubrica,
                itens=title,
                contexto_plan=section_content
            )
            resp = run_inference_with_failover(prompt, json_schema=schema, task_type="reasoning")
            if not resp or not resp.content:
                print(f"🚫 Seção '{title}': BLOCK (Falha de inferência)", file=sys.stderr)
                return 1

            parsed = self.parse_structured_evaluation(resp)
            print(f"[{resp.provider}: {resp.model}] {title} -> {parsed.get('verdict')}", file=sys.stderr)
            if parsed.get("exit_code", 1) != 0:
                overall_exit_code = 1
                overall_verdict = "BLOCK"
                if parsed.get("critique"):
                    print(f"  Critique: {parsed['critique']}", file=sys.stderr)
                if parsed.get("suggested_fix"):
                    print(f"  Fix: {parsed['suggested_fix']}", file=sys.stderr)

        print("----------------------------------------------------------------", file=sys.stderr)
        print(f"{'✅' if overall_exit_code == 0 else '🚫'} VEREDICTO FINAL: {overall_verdict}", file=sys.stderr)
        return overall_exit_code
