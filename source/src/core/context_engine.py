#!/usr/bin/env python3
# context_engine.py | Vitalia Kit — Domínio CORE
# Atualizado em: 28-08-2026 09:00:00(GMT-04:00)
"""
Orquestrador Mestre de Controle de Contexto 3-Tier — Vitalia Kit (Domínio CORE)

Responsabilidades:
1. Coordenar os fluxos de ciclo de vida de contexto:
   - --action init: Cria a estrutura de diretórios e arquivos iniciais em .vitalia/memory/session.
   - --action consolidate: Executa normalização de memória, adquire lock, deduplica shards,
     compila README.md (via dashboard_template.md), SESSION_STATE.md, LEARNINGS.md e emite telemetria.
   - --action end: Executa a persistência atômica da Fase 2 do workflow session-end por script nativo.
   - --action shard: Grava ou atualiza o shard da máquina local de forma determinística.
   - --action lock / unlock / status: Gerencia o semáforo de concorrência com lease token e TTL.

Didática para Desenvolvedores Iniciantes:
- O ContextEngine funciona como a 'Fachada' (Facade Pattern) do sistema. Em vez de chamar o ShardManager,
  o SemaphoreManager e o DashboardRenderer separadamente, a CLI chama apenas o ContextEngine, que
  orquestra a ordem exata de cada etapa sem risco de inconsistência.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional

# Auto-injeção do diretório pai em sys.path
_scripts_root = str(Path(__file__).resolve().parent.parent)
if _scripts_root not in sys.path:
    sys.path.insert(0, _scripts_root)

import kit_env_bootstrap
health = kit_env_bootstrap.init()
from core.utils import get_timestamp, read_jsonl, append_jsonl, generate_id
from core.semaphore_manager import SemaphoreManager
from core.shard_manager import ShardManager
from core.event_publisher import EventPublisher
from rendering.dashboard_renderer import DashboardRenderer
from rendering.view_renderer import ViewRenderer
from rendering.grounding_renderer import GroundingRenderer
from maintenance.jsonl_normalizer import JSONLNormalizer


class ContextEngine:
    """
    Orquestrador central de estado, concorrência e renderização de memória 3-Tier.
    """
    def __init__(self, session_dir: Optional[Path] = None):
        self.project_root = kit_env_bootstrap.find_project_root()
        self.session_dir = session_dir or (self.project_root / ".vitalia" / "memory" / "session")
        self.semaphore_mgr = SemaphoreManager(self.session_dir)
        self.shard_mgr = ShardManager(self.session_dir)
        self.event_pub = EventPublisher(self.session_dir)
        self.dashboard_renderer = DashboardRenderer(self.session_dir)
        self.view_renderer = ViewRenderer(self.session_dir)
        self.grounding_renderer = GroundingRenderer(self.session_dir)
        self.normalizer = JSONLNormalizer(self.session_dir)

    def action_init(self) -> None:
        """Inicializa repositório de memória de contexto em novo projeto."""
        print(f"[ContextEngine] Inicializando estrutura em: {self.session_dir}")
        (self.session_dir / "data").mkdir(parents=True, exist_ok=True)
        (self.session_dir / "shards").mkdir(parents=True, exist_ok=True)
        (self.session_dir / "state").mkdir(parents=True, exist_ok=True)

        self.semaphore_mgr.read_semaphore()  # Cria semaphore.json se ausente
        self.grounding_renderer.compile()
        print("[ContextEngine] ✅ Estrutura inicial criada com sucesso!")

    def action_consolidate(self) -> None:
        """Executa a consolidação de memória completa, normalização e renderização das views."""
        print(f"[ContextEngine] 🔄 Iniciando consolidação em: {self.session_dir}")

        # 1. Normalizar dados pré-consolidação
        total_l, fixed_l = self.normalizer.normalize_learnings()
        total_d, fixed_d = self.normalizer.normalize_decisions()
        migrated_shards = self.normalizer.migrate_legacy_shards()
        if fixed_l > 0 or fixed_d > 0 or migrated_shards > 0:
            print(f"  🧹 Normalização: {fixed_l} aprendizados e {fixed_d} decisões corrigidos | {migrated_shards} shards migrados")

        # 2. Ler estado e dados
        sem_data = self.semaphore_mgr.read_semaphore()
        shards = self.shard_mgr.load_all_shards()
        history = read_jsonl(self.session_dir / "data" / "session_history.jsonl")
        decisions = read_jsonl(self.session_dir / "data" / "decisions.jsonl")
        learnings = read_jsonl(self.session_dir / "data" / "learnings.jsonl")

        # 3. Compilar README.md via template canônico
        readme_content = self.dashboard_renderer.render(sem_data, shards, history, decisions)
        (self.session_dir / "README.md").write_text(readme_content, encoding="utf-8")

        # 4. Compilar Pure Rendered Views
        active_shard = shards[0] if shards else None
        state_content = self.view_renderer.render_session_state(active_shard, sem_data)
        (self.session_dir / "SESSION_STATE.md").write_text(state_content, encoding="utf-8")

        decisions_content = self.view_renderer.render_decisions(decisions)
        (self.session_dir / "DECISIONS.md").write_text(decisions_content, encoding="utf-8")

        learnings_content = self.view_renderer.render_learnings(learnings)
        (self.session_dir / "LEARNINGS.md").write_text(learnings_content, encoding="utf-8")

        history_content = self.view_renderer.render_session_history(history)
        (self.session_dir / "SESSION_HISTORY.md").write_text(history_content, encoding="utf-8")

        # 5. Compilar grounding
        self.grounding_renderer.compile()

        # 6. Emitir telemetria
        self.event_pub.emit_event("CONTEXT_CONSOLIDATED", {
            "shards_count": len(shards),
            "learnings_count": len(learnings),
            "decisions_count": len(decisions)
        })

        print(f"[ContextEngine] ✅ Consolidação concluída: {len(shards)} estações | README.md e Pure Views compiladas!")

    def action_end(self, task: str, p0: str, summary: str, learnings_json: str = "[]", decisions_json: str = "[]") -> None:
        """
        Executa o encerramento estruturado de sessão (Fase 2 do session-end).
        """
        machine_name = os.environ.get("VITALIA_MACHINE_NAME", "andrenote")
        machine_id = os.environ.get("VITALIA_MACHINE_ID", generate_id(machine_name, length=8))
        mode = "Integrado" if health.get("redis_client_ok", False) else "Standalone"

        print(f"[ContextEngine] 🏁 Encerrando sessão para máquina '{machine_name}' ({machine_id})...")

        # 1. Parse dos aprendizados e decisões
        try:
            learnings = json.loads(learnings_json) if isinstance(learnings_json, str) else learnings_json
        except Exception:
            learnings = []

        try:
            decisions = json.loads(decisions_json) if isinstance(decisions_json, str) else decisions_json
        except Exception:
            decisions = []

        # 2. Append em data/learnings.jsonl
        learnings_file = self.session_dir / "data" / "learnings.jsonl"
        for item in learnings:
            rec = {
                "id": generate_id(str(item.get("learning", "")) + get_timestamp()),
                "timestamp": get_timestamp(),
                "machine_id": machine_id,
                "source_origin": machine_name,
                "category": item.get("category", "[PROJETO]"),
                "learning": item.get("learning", ""),
                "rationale": item.get("rationale", "Registro defasado"),
                "trigger_event": item.get("trigger_event", "session-end")
            }
            append_jsonl(learnings_file, rec)

        # 3. Append em data/decisions.jsonl
        decisions_file = self.session_dir / "data" / "decisions.jsonl"
        for item in decisions:
            rec = {
                "id": generate_id(str(item.get("decision", "")) + get_timestamp()),
                "timestamp": get_timestamp(),
                "machine_id": machine_id,
                "category": item.get("category", "[ARCH]"),
                "decision": item.get("decision", ""),
                "rationale": item.get("rationale", "Registro defasado"),
                "alternatives": item.get("alternatives", [])
            }
            append_jsonl(decisions_file, rec)

        # 4. Gravar histórico da sessão
        history_file = self.session_dir / "data" / "session_history.jsonl"
        append_jsonl(history_file, {
            "timestamp": get_timestamp(),
            "machine_id": machine_id,
            "machine_name": machine_name,
            "task": task,
            "summary": summary,
            "next_step": p0,
            "mode": mode
        })

        # 5. Atualizar shard da máquina local
        self.shard_mgr.write_shard(
            machine_id=machine_id,
            machine_name=machine_name,
            task=task,
            status="Concluído",
            next_step=p0,
            steps=[summary],
            mode=mode
        )

        # 6. Recompilar visões
        self.action_consolidate()
        print("[ContextEngine] ✅ Sessão encerrada com sucesso e dados estruturados persistidos!")
