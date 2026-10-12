#!/usr/bin/env python3
# sdd_task_runner.py | Atualizado em: 21-09-2026 22:03:15(GMT-04:00)
# sdd_task_runner.py | Vitalia SDD v0.6.0 | 21-09-2026 21:47(GMT-04:00)
"""
Orquestrador Granular de Tasks do Ciclo SDD.

Lê o tasks.md de uma feature, extrai tarefas pendentes [ ] T00x uma a uma,
entrega contexto prunado para execução, aciona o gate constitucional
(sdd_judge --mode after_task) e marca [X] somente após veredicto PASS.

Modos de operação:
  interactive  — pausa em cada BLOCK para decisão humana (HITL)
  auto         — tenta autocorrigir via LLM até --max-retries; escalona ao humano se esgotar

Exit codes:
  0  — todas as tasks concluídas com sucesso
  1  — execução interrompida (BLOCK não resolvido ou erro de leitura)
  2  — INFRA_FAIL (Gemini API + Ollama indisponíveis)

Exemplos:
  # Modo interativo — pausa a cada BLOCK para decisão humana:
  python3 sdd_task_runner.py --feature specs/005-sdd-governance-hybrid-routing --mode interactive

  # Modo autônomo — LLM tenta corrigir até 3 vezes antes de escalonar:
  python3 sdd_task_runner.py --feature specs/005 --mode auto --max-retries 3

  # Retomar a partir de uma task específica (após crash):
  python3 sdd_task_runner.py --feature specs/005 --mode interactive --start-from T005

  # Listar tasks pendentes sem executar:
  python3 sdd_task_runner.py --feature specs/005 --list-pending
"""

import os
import sys
import re
import json
import argparse
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple

# ── Adicionar o caminho do kit ao sys.path para importar providers ──────────
_KIT_SRC = Path(os.environ.get("VITALIA_KIT_DIR", Path.home() / ".vitalia")) / "src"
_KIT_HOOKS = _KIT_SRC / "hooks"
for _p in [str(_KIT_SRC), str(_KIT_HOOKS)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from sdd_judge.providers import run_inference_with_failover, InfraFailError, EXIT_INFRA_FAIL
    _PROVIDERS_OK = True
except ImportError:
    _PROVIDERS_OK = False

# ── Constantes ───────────────────────────────────────────────────────────────
TASK_PATTERN    = re.compile(r"^(\s*-\s*)\[\s\]\s*(T\d+)", re.MULTILINE)
DONE_MARKER     = "[X]"
MAX_CONTEXT_LEN = 8_000  # chars — truncamento do arquivo-alvo
EXIT_OK         = 0
EXIT_BLOCK      = 1


# ─── Funções de parse do tasks.md ────────────────────────────────────────────

def load_tasks_md(feature_dir: Path) -> str:
    """Lê e retorna o conteúdo do tasks.md da feature."""
    tasks_file = feature_dir / "tasks.md"
    if not tasks_file.exists():
        raise FileNotFoundError(f"tasks.md não encontrado em: {tasks_file}")
    return tasks_file.read_text(encoding="utf-8")


def save_tasks_md(feature_dir: Path, content: str) -> None:
    """Salva o conteúdo atualizado no tasks.md."""
    tasks_file = feature_dir / "tasks.md"
    tasks_file.write_text(content, encoding="utf-8")


def extract_pending_tasks(content: str) -> List[Tuple[str, str]]:
    """Retorna lista de (task_id, linha_completa) para tasks pendentes [ ]."""
    results = []
    for line in content.splitlines():
        m = re.match(r"^\s*-\s*\[\s\]\s*(T\d+)\s+(.*)", line)
        if m:
            results.append((m.group(1), line.strip()))
    return results


def mark_task_done(content: str, task_id: str) -> str:
    """Substitui '[ ] T00x' por '[X] T00x' no tasks.md (in-place, regex)."""
    pattern = re.compile(
        r"^(\s*-\s*)\[\s\]\s*(" + re.escape(task_id) + r")\b",
        re.MULTILINE
    )
    return pattern.sub(r"\1[X] \2", content, count=1)


def extract_target_file(task_line: str) -> Optional[Path]:
    """Heurística: extrai o último token com '/' ou extensão conhecida da linha da task."""
    exts = {".py", ".md", ".toml", ".yaml", ".yml", ".json", ".sh", ".txt"}
    tokens = task_line.split()
    for token in reversed(tokens):
        token = token.strip("`*\"'()")
        if "/" in token or Path(token).suffix in exts:
            return Path(token)
    return None


def build_context_payload(task_id: str, task_line: str, project_root: Path) -> dict:
    """Monta o payload de contexto para a task: id, descrição, arquivo-alvo e snippet."""
    target_file = extract_target_file(task_line)
    target_snippet = ""

    if target_file:
        # Resolver relativo ao project_root ou home
        candidates = [
            project_root / target_file,
            Path(str(target_file).replace("~", str(Path.home()))),
            target_file,
        ]
        for candidate in candidates:
            if candidate.exists():
                try:
                    content = candidate.read_text(encoding="utf-8", errors="ignore")
                    if len(content) > MAX_CONTEXT_LEN:
                        content = content[:MAX_CONTEXT_LEN] + "\n\n[... truncado ...]"
                    target_snippet = content
                except OSError:
                    pass
                break

    return {
        "task_id": task_id,
        "task_description": task_line,
        "target_file": str(target_file) if target_file else None,
        "target_content_snippet": target_snippet,
    }


# ─── Gate constitucional ─────────────────────────────────────────────────────

def run_judge(kit_src: Path) -> int:
    """Invoca sdd_judge --mode after_task como subprocess isolado. Retorna exit code."""
    judge_path = kit_src / "hooks" / "sdd_judge.py"
    cmd = f"python3 {judge_path} --mode after_task"
    result = subprocess.run(cmd, shell=True)
    return result.returncode


# ─── Modos de execução ───────────────────────────────────────────────────────

def present_context(payload: dict) -> None:
    """Exibe o contexto prunado da task para o usuário/IA."""
    print(f"\n{'='*60}")
    print(f"🎯 Task: {payload['task_id']}")
    print(f"   {payload['task_description']}")
    if payload["target_file"]:
        print(f"   Arquivo-alvo: {payload['target_file']}")
    if payload["target_content_snippet"]:
        print(f"\n--- Contexto do arquivo-alvo (primeiros {MAX_CONTEXT_LEN} chars) ---")
        print(payload["target_content_snippet"][:500] + ("..." if len(payload["target_content_snippet"]) > 500 else ""))
    print(f"{'='*60}")


def run_interactive(feature_dir: Path, kit_src: Path, start_from: Optional[str]) -> int:
    """Modo interativo: pausa em cada BLOCK para decisão HITL."""
    content = load_tasks_md(feature_dir)
    pending = extract_pending_tasks(content)

    if not pending:
        print("✅ Nenhuma task pendente. tasks.md já está concluído.")
        return EXIT_OK

    # Filtrar --start-from se especificado
    if start_from:
        idx = next((i for i, (tid, _) in enumerate(pending) if tid == start_from), None)
        if idx is None:
            print(f"❌ Task '{start_from}' não encontrada entre as pendentes.", file=sys.stderr)
            return EXIT_BLOCK
        pending = pending[idx:]

    project_root = Path.cwd()

    for task_id, task_line in pending:
        payload = build_context_payload(task_id, task_line, project_root)
        present_context(payload)

        print(f"\n⏳ Execute a task {task_id} e pressione ENTER quando concluir (ou 's' para skipear): ", end="")
        user_input = input().strip().lower()

        if user_input == "s":
            print(f"⏭️  {task_id} skipada.")
            continue

        # Acionar gate constitucional
        exit_code = run_judge(kit_src)

        if exit_code == EXIT_OK:
            content = load_tasks_md(feature_dir)
            content = mark_task_done(content, task_id)
            save_tasks_md(feature_dir, content)
            print(f"✅ {task_id} → [X] (PASS)")

        elif exit_code == EXIT_INFRA_FAIL:
            print(f"\n🔌 INFRA_FAIL ao auditar {task_id}.", file=sys.stderr)
            print("   Opções: [r]etentar judge / [s]kipear task / [a]bortar runner", end=" ")
            choice = input().strip().lower()
            if choice == "r":
                # Retry simples
                exit_code2 = run_judge(kit_src)
                if exit_code2 == EXIT_OK:
                    content = load_tasks_md(feature_dir)
                    content = mark_task_done(content, task_id)
                    save_tasks_md(feature_dir, content)
                    print(f"✅ {task_id} → [X] (PASS após retry)")
                else:
                    print(f"⚠️  {task_id} não marcada. Continuando...")
            elif choice == "a":
                print("🛑 Runner abortado pelo usuário.")
                return EXIT_BLOCK

        else:  # BLOCK constitucional
            print(f"\n🚫 BLOCK em {task_id}. Corrija e tente novamente.")
            print("   Opções: [c]ontinuar (retentar judge) / [s]kipear task: ", end="")
            choice = input().strip().lower()
            if choice == "c":
                exit_code2 = run_judge(kit_src)
                if exit_code2 == EXIT_OK:
                    content = load_tasks_md(feature_dir)
                    content = mark_task_done(content, task_id)
                    save_tasks_md(feature_dir, content)
                    print(f"✅ {task_id} → [X] (PASS após correção)")

    print("\n🏁 Runner interativo concluído.")
    return EXIT_OK


def run_auto(feature_dir: Path, kit_src: Path, max_retries: int, start_from: Optional[str]) -> int:
    """Modo autônomo: LLM tenta autocorrigir via feedback do judge até max_retries."""
    if not _PROVIDERS_OK:
        print("❌ Providers do sdd_judge não disponíveis. Use --mode interactive.", file=sys.stderr)
        return EXIT_BLOCK

    content = load_tasks_md(feature_dir)
    pending = extract_pending_tasks(content)

    if not pending:
        print("✅ Nenhuma task pendente.")
        return EXIT_OK

    if start_from:
        idx = next((i for i, (tid, _) in enumerate(pending) if tid == start_from), None)
        if idx is None:
            print(f"❌ Task '{start_from}' não encontrada.", file=sys.stderr)
            return EXIT_BLOCK
        pending = pending[idx:]

    project_root = Path.cwd()

    for task_id, task_line in pending:
        payload = build_context_payload(task_id, task_line, project_root)
        print(f"\n🤖 [auto] Processando {task_id}: {task_line[:80]}...")

        retries = 0
        while retries <= max_retries:
            exit_code = run_judge(kit_src)

            if exit_code == EXIT_OK:
                content = load_tasks_md(feature_dir)
                content = mark_task_done(content, task_id)
                save_tasks_md(feature_dir, content)
                print(f"✅ {task_id} → [X] (PASS na tentativa {retries + 1})")
                break

            elif exit_code == EXIT_INFRA_FAIL:
                # INFRA_FAIL: escalonar imediatamente para HITL
                print(f"\n🔌 INFRA_FAIL em {task_id}. Escalando para modo interativo.", file=sys.stderr)
                print("   [r]etentar / [s]kipear / [a]bortar: ", end="")
                choice = input().strip().lower()
                if choice == "s":
                    break
                elif choice == "a":
                    return EXIT_BLOCK
                # "r" → continua o loop

            else:
                # BLOCK constitucional — tentar autocorreção com feedback do LLM
                retries += 1
                if retries > max_retries:
                    print(f"🚫 {task_id} esgotou {max_retries} tentativas. Escalando para HITL.")
                    print("   [c]ontinuar manualmente / [s]kipear / [a]bortar: ", end="")
                    choice = input().strip().lower()
                    if choice == "s":
                        break
                    elif choice == "a":
                        return EXIT_BLOCK
                    break
                else:
                    print(f"⚠️  BLOCK em {task_id} (tentativa {retries}/{max_retries}). Injetando feedback ao LLM...")
                    feedback_prompt = (
                        f"A task {task_id} foi auditada e recebeu BLOCK constitucional. "
                        f"Descrição da task: {task_line}\n"
                        f"Por favor, corrija o código ou a implementação para atender aos critérios constitucionais."
                    )
                    try:
                        _ = run_inference_with_failover(feedback_prompt)
                    except InfraFailError:
                        print(f"🔌 INFRA_FAIL durante feedback LLM. Escalando.", file=sys.stderr)
                        return EXIT_INFRA_FAIL

    print("\n🏁 Runner autônomo concluído.")
    return EXIT_OK


# ─── CLI principal ────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="sdd_task_runner.py",
        description="Orquestrador Granular de Tasks do Ciclo SDD (Vitalia Kit v0.6.0)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Modo interativo — pausa a cada BLOCK para decisão humana:
  python3 sdd_task_runner.py --feature specs/005-sdd-governance-hybrid-routing --mode interactive

  # Modo autônomo — tenta corrigir até 3 vezes antes de escalonar:
  python3 sdd_task_runner.py --feature specs/005 --mode auto --max-retries 3

  # Retomar a partir de uma task específica após interrupção:
  python3 sdd_task_runner.py --feature specs/005 --mode interactive --start-from T005

  # Listar tasks pendentes sem executar:
  python3 sdd_task_runner.py --feature specs/005 --list-pending

Exit codes:
  0  — todas as tasks concluídas (ou sem pendentes)
  1  — BLOCK não resolvido / execução interrompida pelo usuário
  2  — INFRA_FAIL (Gemini API + Ollama indisponíveis)
"""
    )
    parser.add_argument(
        "--feature", required=True, metavar="PATH",
        help="Caminho do diretório da feature (ex: specs/005-sdd-governance-hybrid-routing)"
    )
    parser.add_argument(
        "--mode", choices=["interactive", "auto"], default="interactive",
        help="Modo de execução: 'interactive' (HITL) ou 'auto' (LLM autocorrige). Padrão: interactive"
    )
    parser.add_argument(
        "--max-retries", type=int, default=3, metavar="N",
        help="Número máximo de tentativas de autocorreção no modo auto. Padrão: 3"
    )
    parser.add_argument(
        "--start-from", metavar="T00x",
        help="Retomar a partir de uma task específica (ex: T005). Idempotente após crash."
    )
    parser.add_argument(
        "--list-pending", action="store_true",
        help="Listar tasks pendentes e sair sem executar"
    )

    args = parser.parse_args()

    feature_dir = Path(args.feature)
    if not feature_dir.exists():
        print(f"❌ Diretório da feature não encontrado: {feature_dir}", file=sys.stderr)
        return EXIT_BLOCK

    kit_src = Path(os.environ.get("VITALIA_KIT_DIR", Path.home() / ".vitalia")) / "src"

    # Modo --list-pending
    if args.list_pending:
        content = load_tasks_md(feature_dir)
        pending = extract_pending_tasks(content)
        if not pending:
            print("✅ Nenhuma task pendente.")
        else:
            print(f"📋 {len(pending)} task(s) pendente(s):")
            for tid, line in pending:
                print(f"  {line}")
        return EXIT_OK

    # Executar modo selecionado
    if args.mode == "interactive":
        return run_interactive(feature_dir, kit_src, args.start_from)
    else:
        return run_auto(feature_dir, kit_src, args.max_retries, args.start_from)


if __name__ == "__main__":
    sys.exit(main())
