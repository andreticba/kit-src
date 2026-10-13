# tasks.py | Vitalia SDD v0.6.0 | 12-10-2026 21:12(GMT-04:00)
import sys
import re
import time
from typing import List, Dict, Tuple, Any
from sdd_judge.evaluators.base import BaseEvaluator
from sdd_judge.prompts.loader import load_prompt_template
from sdd_judge.providers import run_inference_with_failover


class TasksEvaluator(BaseEvaluator):
    """Estratégia de auditoria constitucional de tarefas em isolamento atômico 1-a-1 com varredura completa (FR-001, FR-004, FR-005)."""

    def extract_tasks(self, content: str) -> List[Tuple[str, str]]:
        """Extrai a lista determinística de tarefas atômicas (T000-X ou T001 a T0N) com sua linha completa."""
        task_pattern = re.compile(r"^\s*-\s*\[([ xX/])\]\s*(T\d{3}(?:-[A-Z])?)\b(.*)$")
        tasks = []
        for line in content.splitlines():
            m = task_pattern.match(line)
            if m:
                task_id = m.group(2)
                tasks.append((task_id, line.strip()))
        return tasks

    def evaluate(self, target_content: str, feature_name: str) -> int:
        rubrica = self.build_rubric("tasks")
        schema = self.load_contract_schema("task_eval_schema.json")
        tasks = self.extract_tasks(target_content)

        if not tasks:
            print("🚫 Nenhuma tarefa atômica (formato '- [ ] T###') encontrada no documento.", file=sys.stderr)
            return 1

        print(f"[SDDJudge] 🔍 Iniciando auditoria 1-a-1 de {len(tasks)} tarefas atômicas (varredura completa sem fail-fast)...", file=sys.stderr)
        
        results: List[Dict[str, Any]] = []
        t_global_start = time.perf_counter()
        active_provider = "Ollama"
        active_model = "qwen2.5:3b"

        # Varredura completa 1-a-1 (FR-004)
        for idx, (task_id, task_line) in enumerate(tasks, start=1):
            prompt = load_prompt_template(
                "tasks",
                feature_name=feature_name,
                rubrica=rubrica,
                itens=task_line
            )

            resp = run_inference_with_failover(prompt, json_schema=schema, task_type="reasoning")
            if not resp or not resp.content:
                parsed = {
                    "task_id": task_id,
                    "task_line": task_line,
                    "critique": "Falha na inferência da tarefa.",
                    "evidence": "Nenhuma resposta retornada do modelo.",
                    "verdict": "BLOCK",
                    "warn_severity": "EXTREME",
                    "suggested_fix": task_line,
                    "exit_code": 1,
                    "latency": 0.0
                }
            else:
                active_provider = resp.provider
                active_model = resp.model
                parsed = self.parse_structured_evaluation(resp)
                parsed["task_id"] = task_id
                parsed["task_line"] = task_line

            results.append(parsed)
            # Log de progresso em tempo real
            icon = "✅" if parsed.get("exit_code") == 0 else ("⚠️" if "WARN" in parsed.get("verdict", "") else "🚫")
            print(f"[{idx}/{len(tasks)}] {icon} {task_id}: {parsed.get('verdict')} ({parsed.get('latency', 0):.2f}s)", file=sys.stderr)

        total_elapsed = time.perf_counter() - t_global_start

        # Reconciliação determinística 1:1 (FR-005)
        extracted_ids = [t[0] for t in tasks]
        audited_ids = [r["task_id"] for r in results]
        if set(extracted_ids) != set(audited_ids):
            missing = set(extracted_ids) - set(audited_ids)
            print(f"🚫 ERRO DE INTEGRIDADE: Tarefas omitidas da auditoria: {missing}", file=sys.stderr)
            return 1

        # Renderização do Banner Dinâmico e Tabela Consolidada (FR-004, FR-007)
        print(f"\n--- PARECER DO JUIZ [{active_provider}: {active_model} | {total_elapsed:.2f}s total] ---", file=sys.stderr)
        print("\n" + "=" * 92, file=sys.stderr)
        print(f"{'TABELA CONSOLIDADA DE AUDITORIA CONSTITUCIONAL DE TAREFAS':^92}", file=sys.stderr)
        print("=" * 92, file=sys.stderr)
        print(f"| {'Task ID':<7} | {'Veredicto':<10} | {'Severidade':<10} | {'Evidência / Sugestão de Correção (suggested_fix)':<53} |", file=sys.stderr)
        print("|" + "-" * 9 + "|" + "-" * 12 + "|" + "-" * 12 + "|" + "-" * 55 + "|", file=sys.stderr)

        passed_count = 0
        warn_count = 0
        blocked_count = 0

        for r in results:
            v = r.get("verdict", "BLOCK")
            s = r.get("warn_severity", "NONE")
            ec = r.get("exit_code", 1)
            fix = r.get("suggested_fix") or r.get("critique") or "-"
            # Truncar visualmente fix para caber na tabela
            fix_display = (fix[:50] + "...") if len(fix) > 53 else fix

            if ec == 0:
                if "WARN" in v:
                    warn_count += 1
                else:
                    passed_count += 1
            else:
                blocked_count += 1

            print(f"| {r['task_id']:<7} | {v:<10} | {s:<10} | {fix_display:<53} |", file=sys.stderr)

        print("=" * 92, file=sys.stderr)
        print(f"Resumo: Total: {len(results)} | Aprovadas: {passed_count} | Avisos Tolerados: {warn_count} | Bloqueadas: {blocked_count}", file=sys.stderr)
        print("=" * 92 + "\n", file=sys.stderr)

        # Se houver itens bloqueados, listar os suggested_fix completos para o desenvolvedor
        if blocked_count > 0:
            print("🔧 SUGESTÕES DE CORREÇÃO PARA TAREFAS BLOQUEADAS:", file=sys.stderr)
            for r in results:
                if r.get("exit_code") != 0:
                    print(f"\n❌ [{r['task_id']}] Violação: {r.get('critique')}", file=sys.stderr)
                    if r.get("evidence"):
                        print(f"   Evidência: {r.get('evidence')}", file=sys.stderr)
                    if r.get("suggested_fix"):
                        print(f"   👉 Substituição sugerida:\n      {r.get('suggested_fix')}", file=sys.stderr)
            print("\n🚫 VEREDICTO FINAL: BLOCK (Corrija as tarefas indicadas acima)", file=sys.stderr)
            return 1

        if warn_count > 0:
            print("⚠️ VEREDICTO FINAL: WARN (Aprovado com ressalvas toleradas)", file=sys.stderr)
            return 0

        print("✅ VEREDICTO FINAL: PASS (Todas as tarefas atômicas aprovadas)", file=sys.stderr)
        return 0
