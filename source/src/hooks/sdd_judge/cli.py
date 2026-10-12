# cli.py | Atualizado em: 21-09-2026 22:03:15(GMT-04:00)
# cli.py | Vitalia SDD v0.6.0 | 21-09-2026 21:44(GMT-04:00)
import sys
import argparse
from pathlib import Path
from typing import Optional

from sdd_judge.evaluators.specify import SpecifyEvaluator
from sdd_judge.evaluators.plan import PlanEvaluator
from sdd_judge.evaluators.tasks import TasksEvaluator
from sdd_judge.evaluators.clarify import ClarifyEvaluator
from sdd_judge.evaluators.converge import ConvergeEvaluator
from sdd_judge.evaluators.after_task import AfterTaskEvaluator
from sdd_judge.providers import InfraFailError, EXIT_INFRA_FAIL


def main(args_list: Optional[list] = None) -> int:
    try:
        _src_dir = str(Path(__file__).resolve().parent.parent.parent)
        if _src_dir not in sys.path:
            sys.path.insert(0, _src_dir)
        import kit_env_bootstrap
        kit_env_bootstrap.init()
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Gatekeeper Constitucional Vitalia SDD (v0.6.0)")
    parser.add_argument(
        "--mode", required=True,
        choices=["specify", "plan", "tasks", "after_task", "clarify", "converge"],
        help="Fase do ciclo SDD a validar"
    )
    parser.add_argument(
        "file", nargs="?", type=Path,
        help="Arquivo alvo (spec.md, plan.md ou tasks.md). Não necessário para --mode after_task"
    )
    parser.add_argument(
        "--profile", type=Path, default=None,
        help="Caminho alternativo para gp_sdd-judge.yaml"
    )

    parsed = parser.parse_args(args_list if args_list is not None else sys.argv[1:])

    mode = parsed.mode
    target_file = parsed.file
    profile_path = parsed.profile

    if mode != "after_task" and not target_file:
        print(f"🚫 [SDDJudge] Erro: O modo '{mode}' exige um arquivo alvo como argumento.", file=sys.stderr)
        return 1

    feature_name = target_file.parent.name if target_file else "Geral"
    target_content = ""

    if target_file:
        if not target_file.exists():
            print(f"🚫 [SDDJudge] Erro: Arquivo não encontrado: {target_file}", file=sys.stderr)
            return 1
        try:
            target_content = target_file.read_text(encoding="utf-8")
        except Exception as e:
            print(f"🚫 [SDDJudge] Erro ao ler {target_file}: {e}", file=sys.stderr)
            return 1

    print(f"[SDDJudge] Perfil carregado: {profile_path or '~/.vitalia/profiles/gp_sdd-judge.yaml'}", file=sys.stderr)
    print(f"⚖️  [SDDJudge] Modo: [{mode}] | Alvo: [{target_file or 'Git Diff'}]", file=sys.stderr)

    evaluators = {
        "specify": SpecifyEvaluator,
        "plan": PlanEvaluator,
        "tasks": TasksEvaluator,
        "clarify": ClarifyEvaluator,
        "converge": ConvergeEvaluator,
        "after_task": AfterTaskEvaluator
    }

    evaluator_cls = evaluators.get(mode)
    if not evaluator_cls:
        print(f"🚫 [SDDJudge] Modo desconhecido: {mode}", file=sys.stderr)
        return 1

    evaluator = evaluator_cls(profile_path=profile_path)
    try:
        return evaluator.evaluate(target_content, feature_name)
    except InfraFailError as e:
        # FR-010 — INFRA_FAIL: ambos os providers falharam. Não é BLOCK constitucional.
        # Exit code 2 permite que callers distingam INFRA_FAIL de BLOCK sem parsing de texto.
        print(f"\n🔌 VEREDICTO FINAL: INFRA_FAIL (exit code {EXIT_INFRA_FAIL})", file=sys.stderr)
        print(f"   Causa: {e}", file=sys.stderr)
        print("   → Verifique conectividade com Gemini API e se Ollama está rodando.", file=sys.stderr)
        print("   → Este NÃO é um BLOCK constitucional. Reexecute quando a infraestrutura estiver disponível.", file=sys.stderr)
        return EXIT_INFRA_FAIL


if __name__ == "__main__":
    sys.exit(main())
