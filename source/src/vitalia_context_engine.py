#!/usr/bin/env python3
# vitalia_context_engine.py | Vitalia SDD v0.6.0 | 07-09-2026 14:41(GMT-04:00)
"""
Entrypoint CLI de Controle de Contexto — Vitalia Kit (Thin Wrapper)

Este arquivo atua como uma casca leve (<40 linhas) para despachar comandos da CLI
para o orquestrador modular core.context_engine.ContextEngine.

Exemplos de uso:
  python3 vitalia_context_engine.py --action consolidate
  python3 vitalia_context_engine.py --action end --task "Feature 009" --p0 "Testes"
  python3 vitalia_context_engine.py --action init
"""

import os
import sys
import socket
import hashlib
import argparse
from pathlib import Path

# Injeção dinâmica do diretório de scripts em sys.path
_scripts_root = str(Path(__file__).resolve().parent)
if _scripts_root not in sys.path:
    sys.path.insert(0, _scripts_root)

import kit_env_bootstrap
health = kit_env_bootstrap.init()
from core.context_engine import ContextEngine


def main():
    parser = argparse.ArgumentParser(
        description="Motor de Controle de Contexto e Sincronização 3-Tier — Vitalia Kit",
        epilog="""Exemplos práticos de uso:
  1. Consolidar memória e recompilar painel README.md:
     python3 vitalia_context_engine.py --action consolidate
  2. Encerramento de sessão estruturado (Fase 2 do session-end):
     python3 vitalia_context_engine.py --action end --task "Nome da Feature" --p0 "Próximo passo"
  3. Inicializar contexto em novo projeto:
     python3 vitalia_context_engine.py --action init
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--action", required=True, choices=["init", "consolidate", "end", "shard", "lock", "unlock", "status"], help="Ação a ser executada")
    parser.add_argument("--session-dir", default=None, help="Caminho customizado de .vitalia/memory/session")
    parser.add_argument("--task", default="", help="Descrição da tarefa ativa")
    parser.add_argument("--p0", default="", help="Próximo passo prioritário (P0)")
    parser.add_argument("--summary", default="", help="Resumo das atividades da sessão")
    parser.add_argument("--learnings-json", default="[]", help="Array JSON de aprendizados estruturados")
    parser.add_argument("--decisions-json", default="[]", help="Array JSON de decisões de arquitetura")
    parser.add_argument("--status", default="Em Andamento", help="Status da estação (ex: Concluído)")
    parser.add_argument("--next-step", default="", help="Alias para P0")
    parser.add_argument("--mode", default="auto", help="Modo de operação (Integrado / Standalone / auto)")

    args = parser.parse_args()

    session_path = Path(args.session_dir) if args.session_dir else None
    engine = ContextEngine(session_path)

    if args.action == "init":
        engine.action_init()
    elif args.action == "consolidate":
        engine.action_consolidate()
    elif args.action == "end":
        engine.action_end(
            task=args.task,
            p0=args.p0 or args.next_step,
            summary=args.summary,
            learnings_json=args.learnings_json,
            decisions_json=args.decisions_json
        )
    elif args.action == "shard":
        # P11: machine_name e machine_id derivados dinamicamente — nunca hardcoded.
        # Precedência: VITALIA_MACHINE_NAME env var → socket.gethostname() → "unknown"
        _mname = os.environ.get("VITALIA_MACHINE_NAME") or socket.gethostname().lower() or "unknown"
        _mid = hashlib.sha256(_mname.encode()).hexdigest()[:8]
        engine.shard_mgr.write_shard(
            machine_id=_mid,
            machine_name=_mname,
            task=args.task,
            status=args.status,
            next_step=args.next_step or args.p0,
            steps=[args.summary] if args.summary else [],
            mode="Integrado" if health.get("redis_client_ok", False) else "Standalone"
        )
        print(f"✅ Shard atualizado com sucesso! [{_mname} / {_mid}]")
    elif args.action == "lock":
        _mname = os.environ.get("VITALIA_MACHINE_NAME") or socket.gethostname().lower() or "unknown"
        _mid = hashlib.sha256(_mname.encode()).hexdigest()[:8]
        ok, token = engine.semaphore_mgr.acquire(_mname, _mid, reason="Lock manual via CLI")
        print(f"{'✅ Lock adquirido! Token: ' + token if ok else '❌ Falha ao adquirir lock: ' + token}")
    elif args.action == "unlock":
        engine.semaphore_mgr.release("", force=True)
        print("✅ Semáforo liberado com sucesso!")
    elif args.action == "status":
        sem = engine.semaphore_mgr.read_semaphore()
        print(f"Semáforo: {sem.get('state')} | Detentor: {sem.get('machine_name')} | Expira em: {sem.get('expires_at')}")


if __name__ == "__main__":
    main()
