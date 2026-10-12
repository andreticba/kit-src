#!/usr/bin/env python3
# event_publisher.py | Vitalia Kit — Domínio CORE
# Atualizado em: 28-08-2026 09:20:00(GMT-04:00)
"""
Publicador de Eventos e Sincronização Git — Vitalia Kit (Domínio CORE)

Responsabilidades:
1. Sincronizar o repositório Git de memória (.vitalia/memory/session) de forma não-bloqueante.
2. Executar add, commit e push automáticos em cada consolidação.
3. Usar GIT_TERMINAL_PROMPT=0, GIT_SSH_COMMAND com BatchMode=yes e timeout de 15s para
   impedir congelamento de terminal por pedidos interativos de credenciais ou passphrases.
4. Modo Integrado: Publicar eventos no Redis Stream 'vitalia:events'.
5. Modo Standalone: Fazer append de eventos em data/events.jsonl.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

_scripts_root = str(Path(__file__).resolve().parent.parent)
if _scripts_root not in sys.path:
    sys.path.insert(0, _scripts_root)

import kit_env_bootstrap
health = kit_env_bootstrap.init()
from core.utils import get_timestamp, append_jsonl


class EventPublisher:
    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.data_dir = session_dir / "data"
        self.events_file = self.data_dir / "events.jsonl"
        self._redis_client = self._init_redis_client()

    def _init_redis_client(self) -> Optional[Any]:
        if not health.get("redis_client_ok", False):
            return None
        try:
            import redis
            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
            client = redis.from_url(redis_url, decode_responses=True, socket_timeout=2.0)
            client.ping()
            return client
        except Exception:
            return None

    def git_sync(self, commit_msg: Optional[str] = None) -> bool:
        """
        Executa add, commit, pull --rebase e push transparentes no repositório de contexto.
        """
        if not (self.session_dir / ".git").exists():
            return False

        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes -o ConnectTimeout=5"

        try:
            # 1. git add -A
            subprocess.run(["git", "-C", str(self.session_dir), "add", "-A"], env=env, capture_output=True, timeout=10)

            # 2. git commit (se houver mudanças pendentes)
            status_proc = subprocess.run(["git", "-C", str(self.session_dir), "status", "--porcelain"], env=env, capture_output=True, text=True, timeout=5)
            if status_proc.stdout.strip():
                msg = commit_msg or f"chore(context): auto-consolidação [{get_timestamp()}]"
                subprocess.run(["git", "-C", str(self.session_dir), "commit", "-m", msg], env=env, capture_output=True, text=True, timeout=10)

            # 3. git pull --rebase
            subprocess.run(["git", "-C", str(self.session_dir), "pull", "--rebase"], env=env, capture_output=True, text=True, timeout=15)

            # 4. git push
            push_proc = subprocess.run(["git", "-C", str(self.session_dir), "push"], env=env, capture_output=True, text=True, timeout=15)
            if push_proc.returncode != 0:
                print(f"ℹ️ [EventPublisher] Push remoto pendente (autenticação SSH requerida localmente): {push_proc.stderr.strip()}", file=sys.stderr)
                return False

            return True
        except subprocess.TimeoutExpired:
            print("⚠️ [EventPublisher] Timeout de 15s no Git. Operando em modo offline.", file=sys.stderr)
            return False
        except Exception as e:
            print(f"⚠️ [EventPublisher] Erro ao sincronizar Git: {e}", file=sys.stderr)
            return False

    def emit_event(self, event_type: str, payload: Dict[str, Any]) -> bool:
        event_record = {
            "timestamp": get_timestamp(),
            "event_type": event_type,
            "payload": payload
        }

        if self._redis_client:
            try:
                import json
                self._redis_client.xadd("vitalia:events", {"data": json.dumps(event_record, ensure_ascii=False)}, maxlen=1000)
            except Exception as e:
                print(f"⚠️ [EventPublisher] Falha ao publicar no Redis Stream: {e}", file=sys.stderr)

        return append_jsonl(self.events_file, event_record)
