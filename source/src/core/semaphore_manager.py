#!/usr/bin/env python3
# semaphore_manager.py | Vitalia Kit — Domínio CORE
# Atualizado em: 28-08-2026 09:00:00(GMT-04:00)
"""
Gerenciador de Concorrência e Semáforo Distribuído — Vitalia Kit (Domínio CORE)

Responsabilidades:
1. Gerenciar o lock de sincronização multi-máquina no arquivo state/semaphore.json.
2. Modo Integrado: Adquire lock atômico no Redis via `SET semaphore:lock <machine_id> NX EX 300`
   e espelha os dados em state/semaphore.json.
3. Modo Standalone: Executa lock atômico em arquivo utilizando renomeação atômica (os.replace).
4. Auto-Expiração por TTL (5 minutos): Se o semáforo estiver LOCKED mas o timestamp atual exceder
   'expires_at', o lock é considerado automaticamente liberado (FREE).
5. Compatibilidade retroativa com campos legados ('status' -> 'state', 'LIVRE' -> 'FREE').
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

_scripts_root = str(Path(__file__).resolve().parent.parent)
if _scripts_root not in sys.path:
    sys.path.insert(0, _scripts_root)

import kit_env_bootstrap
health = kit_env_bootstrap.init()
from core.utils import get_current_datetime, get_timestamp, generate_id, VITALIA_TIMEZONE


class SemaphoreManager:
    """
    Controlador de concorrência que previne colisões multi-máquina e deadlocks por TTL.
    """
    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.state_dir = session_dir / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.semaphore_file = self.state_dir / "semaphore.json"
        self.ttl_minutes = 5
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

    def read_semaphore(self) -> Dict[str, Any]:
        """Lê o estado atual do semáforo com tratamento de auto-expiração por TTL e normalização."""
        default_state = {
            "state": "FREE",
            "locked_by": "",
            "machine_name": "",
            "locked_at": "",
            "expires_at": "",
            "lease_token": "",
            "lock_reason": ""
        }
        if not self.semaphore_file.exists():
            self._write_file(default_state)
            return default_state

        try:
            raw = json.loads(self.semaphore_file.read_text(encoding="utf-8"))
            # Normalizar campos legados
            state_val = raw.get("state") or raw.get("status") or "FREE"
            if state_val in ["LIVRE", "FREE", "free", "livre"]:
                state_val = "FREE"
            elif state_val in ["LOCKED", "locked", "BLOQUEADO"]:
                state_val = "LOCKED"

            data = {
                "state": state_val,
                "locked_by": raw.get("locked_by") or raw.get("machine_id") or "",
                "machine_id": raw.get("machine_id") or raw.get("locked_by") or "",
                "machine_name": raw.get("machine_name") or "unknown",
                "locked_at": raw.get("locked_at") or raw.get("updated_at") or "",
                "expires_at": raw.get("expires_at") or "",
                "lease_token": raw.get("lease_token") or "",
                "lock_reason": raw.get("lock_reason") or ""
            }

            # Checar auto-expiração por TTL
            if data.get("state") == "LOCKED":
                expires_str = data.get("expires_at", "")
                if expires_str:
                    try:
                        clean_ts = expires_str.replace("(GMT-04:00)", "").strip()
                        expires_dt = datetime.strptime(clean_ts, "%d-%m-%Y %H:%M:%S").replace(tzinfo=VITALIA_TIMEZONE)
                        if get_current_datetime() > expires_dt:
                            print(f"ℹ️ [Semaphore] Lock da máquina {data.get('machine_name')} expirou por TTL. Liberando automaticamente.")
                            self.release(data.get("lease_token", ""), force=True)
                            return default_state
                    except Exception as parse_err:
                        print(f"⚠️ [Semaphore] Falha ao checar TTL ({parse_err}). Mantendo estado.", file=sys.stderr)
            return data
        except Exception as e:
            print(f"⚠️ [Semaphore] Falha ao ler {self.semaphore_file}: {e}", file=sys.stderr)
            return default_state

    def _write_file(self, payload: Dict[str, Any]) -> None:
        temp_file = self.semaphore_file.with_suffix(".json.tmp")
        temp_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(temp_file, self.semaphore_file)

    def acquire(self, machine_name: str, machine_id: str, reason: str = "Consolidação de sessão") -> Tuple[bool, str]:
        current = self.read_semaphore()
        if current.get("state") == "LOCKED" and current.get("machine_id") != machine_id:
            msg = f"Bloqueado por {current.get('machine_name')} ({current.get('machine_id')}) até {current.get('expires_at')}"
            return False, msg

        now = get_current_datetime()
        expires_dt = now + timedelta(minutes=self.ttl_minutes)
        lease_token = generate_id(f"{machine_id}_{now.isoformat()}_{os.getpid()}", length=16)

        if self._redis_client:
            try:
                acquired_redis = self._redis_client.set("semaphore:lock", lease_token, nx=True, ex=self.ttl_minutes * 60)
                if not acquired_redis:
                    return False, "Redis: Lock já detido por outro processo concorrente"
            except Exception as e:
                print(f"⚠️ [Semaphore] Redis lock falhou ({e}), operando via fallback em arquivo JSON.", file=sys.stderr)

        payload = {
            "state": "LOCKED",
            "locked_by": machine_id,
            "machine_id": machine_id,
            "machine_name": machine_name,
            "locked_at": get_timestamp(now),
            "expires_at": get_timestamp(expires_dt),
            "lease_token": lease_token,
            "lock_reason": reason
        }

        try:
            self._write_file(payload)
            return True, lease_token
        except Exception as e:
            return False, f"Falha de I/O ao gravar semáforo: {e}"

    def release(self, lease_token: str, force: bool = False) -> bool:
        current = self.read_semaphore()
        if not force and current.get("lease_token") != lease_token and current.get("state") == "LOCKED":
            print(f"❌ [Semaphore] Token inválido ({lease_token}). Impossível liberar lock de {current.get('machine_name')}.")
            return False

        if self._redis_client:
            try:
                self._redis_client.delete("semaphore:lock")
            except Exception:
                pass

        free_payload = {
            "state": "FREE",
            "locked_by": "",
            "machine_id": "",
            "machine_name": "",
            "locked_at": "",
            "expires_at": "",
            "lease_token": "",
            "lock_reason": ""
        }
        try:
            self._write_file(free_payload)
            return True
        except Exception as e:
            print(f"❌ [Semaphore] Falha ao liberar semáforo: {e}", file=sys.stderr)
            return False
