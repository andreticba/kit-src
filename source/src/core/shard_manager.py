#!/usr/bin/env python3
# shard_manager.py | Vitalia Kit — Domínio CORE
# Atualizado em: 28-08-2026 09:00:00(GMT-04:00)
"""
Gerenciador de Shards Multi-Máquina e Deduplicação — Vitalia Kit (Domínio CORE)

Responsabilidades:
1. Leitura e gravação de shards locais e remotos em shards/<machine_id>.yaml no schema canônico v0.5.0.
2. Restauração de 'filter_shards_by_machine': Deduplica múltiplos shards do mesmo machine_name,
   preservando estritamente a entrada com o timestamp 'last_sync' mais recente.
3. Restauração de 'check_staleness': Marca máquinas com inatividade >24h com alerta ⚠️ no dashboard.
4. Restauração de 'upsert_machines_jsonl': Registra o histórico de conexões por máquina em data/machines.jsonl.

Didática para Desenvolvedores Iniciantes:
- O que é um Shard? Cada computador ou estação de trabalho salva seu progresso em um arquivo separado
  (ex: shards/7f367bd3.yaml). Quando você dá `git pull`, os shards de todos os colegas chegam sem conflito.
- Por que deduplicar? Se uma máquina trocar de ID ou reiniciar, múltiplos shards podem ter o mesmo nome.
  O filtro escolhe sempre o mais novo, impedindo duplicação no gráfico Mermaid e nas tabelas.
"""

import os
import sys
import re
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# Auto-injeção do diretório pai em sys.path
_scripts_root = str(Path(__file__).resolve().parent.parent)
if _scripts_root not in sys.path:
    sys.path.insert(0, _scripts_root)

import kit_env_bootstrap
health = kit_env_bootstrap.init()
from core.utils import get_current_datetime, get_timestamp, read_jsonl, append_jsonl, VITALIA_TIMEZONE


class ShardManager:
    """
    CRUD seguro de shards YAML, deduplicação por last_sync e monitoramento de inatividade.
    """
    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.shards_dir = session_dir / "shards"
        self.shards_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = session_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.machines_file = self.data_dir / "machines.jsonl"

    def read_shard(self, shard_path: Path) -> Optional[Dict[str, Any]]:
        """Lê um shard YAML de forma tolerante e retorna um dicionário estruturado."""
        if not shard_path.exists():
            return None

        try:
            content = shard_path.read_text(encoding="utf-8")
            data = {}
            # Parser YAML chave-valor tolerante nativo stdlib
            for line in content.splitlines():
                line_str = line.strip()
                if not line_str or line_str.startswith("#"):
                    continue
                if ":" in line_str and not line_str.startswith("-"):
                    k, v = line_str.split(":", 1)
                    key = k.strip()
                    val = v.strip().strip('"').strip("'")
                    data[key] = val
            return data
        except Exception as e:
            print(f"⚠️ [ShardManager] Erro ao ler shard {shard_path.name}: {e}", file=sys.stderr)
            return None

    def write_shard(self, machine_id: str, machine_name: str, task: str, status: str, next_step: str, steps: List[str], mode: str = "Integrado") -> Path:
        """
        Grava ou atualiza o shard da máquina local no schema canônico v0.5.0.
        """
        shard_path = self.shards_dir / f"{machine_id}.yaml"
        steps_yaml = "\n".join(f'  - "{s}"' for s in steps) if steps else '  - "Sessão iniciada"'

        payload_yaml = f"""schema_version: "0.5.0"
machine_name: "{machine_name}"
machine_id: "{machine_id}"
mode: "{mode}"
current_task: "{task}"
status: "{status}"
next_step: "{next_step}"
last_sync: "{get_timestamp()}"
steps_completed:
{steps_yaml}
"""
        shard_path.write_text(payload_yaml, encoding="utf-8")
        self.upsert_machines_jsonl({
            "machine_id": machine_id,
            "machine_name": machine_name,
            "mode": mode,
            "last_sync": get_timestamp(),
            "last_task": task
        })
        return shard_path

    def load_all_shards(self) -> List[Dict[str, Any]]:
        """Lê todos os shards presentes no diretório shards/."""
        shards = []
        for yaml_file in sorted(self.shards_dir.glob("*.yaml")):
            s = self.read_shard(yaml_file)
            if s:
                shards.append(s)
        return self.filter_shards_by_machine(shards)

    def filter_shards_by_machine(self, shards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplica múltiplos shards com o mesmo 'machine_name', preservando estritamente
        aquele com o 'last_sync' mais recente.
        """
        by_machine: Dict[str, Dict[str, Any]] = {}

        def parse_sync_time(sync_str: str) -> datetime:
            try:
                clean = sync_str.replace("(GMT-04:00)", "").strip()
                return datetime.strptime(clean, "%d-%m-%Y %H:%M:%S").replace(tzinfo=VITALIA_TIMEZONE)
            except Exception:
                return datetime.min.replace(tzinfo=VITALIA_TIMEZONE)

        for shard in shards:
            name = shard.get("machine_name", shard.get("machine_id", "unknown"))
            shard_time = parse_sync_time(shard.get("last_sync", ""))

            if name not in by_machine:
                by_machine[name] = shard
            else:
                existing_time = parse_sync_time(by_machine[name].get("last_sync", ""))
                if shard_time > existing_time:
                    by_machine[name] = shard

        return list(by_machine.values())

    def check_staleness(self, last_sync_str: str) -> bool:
        """
        Retorna True se a última sincronização ocorreu há mais de 24 horas.
        """
        if not last_sync_str:
            return True
        try:
            clean = last_sync_str.replace("(GMT-04:00)", "").strip()
            sync_dt = datetime.strptime(clean, "%d-%m-%Y %H:%M:%S").replace(tzinfo=VITALIA_TIMEZONE)
            return (get_current_datetime() - sync_dt) > timedelta(hours=24)
        except Exception:
            return False

    def upsert_machines_jsonl(self, machine_record: Dict[str, Any]) -> None:
        """Registra no log append-only machines.jsonl."""
        record = {
            "timestamp": get_timestamp(),
            "machine_id": machine_record.get("machine_id", ""),
            "machine_name": machine_record.get("machine_name", ""),
            "mode": machine_record.get("mode", "Integrado"),
            "last_task": machine_record.get("last_task", "")
        }
        append_jsonl(self.machines_file, record)
