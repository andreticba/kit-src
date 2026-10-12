#!/usr/bin/env python3
# view_renderer.py | Vitalia Kit — Domínio RENDERING
# Atualizado em: 28-08-2026 09:00:00(GMT-04:00)
"""
Gerador de Visões Especializadas para IA (Pure Rendered Views) — Vitalia Kit (Domínio RENDERING)
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

_scripts_root = str(Path(__file__).resolve().parent.parent)
if _scripts_root not in sys.path:
    sys.path.insert(0, _scripts_root)

import kit_env_bootstrap
health = kit_env_bootstrap.init()
from core.utils import get_timestamp, format_visible_header, read_jsonl


class ViewRenderer:
    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.data_dir = session_dir / "data"

    def render_session_state(self, active_shard: Optional[Dict[str, Any]], semaphore: Dict[str, Any]) -> str:
        if not active_shard:
            active_shard = {"machine_name": "unknown", "current_task": "Nenhuma", "next_step": "Iniciar sessão", "mode": "Integrado"}

        is_locked = semaphore.get("state") == "LOCKED"
        sem_str = f"LOCKED por {semaphore.get('machine_name')} (até {semaphore.get('expires_at')})" if is_locked else "LIVRE"

        lines = [
            f"<!-- SESSION_STATE.md | Atualizado em: {get_timestamp()} -->",
            "# 📍 Estado Ativo da Sessão Vitalia",
            "",
            format_visible_header(),
            "",
            f"- **Feature / Tarefa Ativa:** {active_shard.get('current_task', '')}",
            f"- **🎯 Próximo Passo Prioritário (P0):** `{active_shard.get('next_step', '')}`",
            f"- **Estação / Modo:** `{active_shard.get('machine_name', '')}` (<code>{active_shard.get('mode', 'Integrado')}</code>)",
            f"- **Semáforo:** {sem_str}",
            f"- **Último Sync:** {get_timestamp()}",
            ""
        ]
        return "\n".join(lines)

    def render_decisions(self, decisions: List[Dict[str, Any]]) -> str:
        lines = [
            f"<!-- DECISIONS.md | Atualizado em: {get_timestamp()} -->",
            "# 🏛️ Decisões de Arquitetura e Governança Consolidadas (ADRs)",
            "",
            format_visible_header(),
            "",
            "| ID | Categoria | Decisão | Racional | Máquina | Data |",
            "|---|---|---|---|---|---|"
        ]
        for d in decisions:
            d_id = d.get("id", "DEC")
            cat = d.get("category", "[ARCH]")
            dec = d.get("decision", "").replace("|", "-")
            rat = d.get("rationale", "Registro defasado").replace("|", "-")
            mac = d.get("machine_id", d.get("machine_name", "unknown"))
            dt = d.get("timestamp", "")
            lines.append(f"| `{d_id}` | `{cat}` | {dec} | {rat} | `{mac}` | {dt} |")

        lines.append("")
        return "\n".join(lines)

    def render_learnings(self, learnings: List[Dict[str, Any]]) -> str:
        lines = [
            f"<!-- LEARNINGS.md | Atualizado em: {get_timestamp()} -->",
            "# 💡 Aprendizados Técnicos e Lições Aprendidas Consolidadas",
            "",
            format_visible_header(),
            ""
        ]
        by_category: Dict[str, List[Dict[str, Any]]] = {}
        for l in learnings:
            cat = l.get("category", "[PROJETO]")
            by_category.setdefault(cat, []).append(l)

        for cat, items in by_category.items():
            lines.append(f"## {cat}")
            for item in items:
                learning = item.get("learning", "")
                rationale = item.get("rationale", "Registro defasado")
                origin = item.get("source_origin", item.get("machine_id", "unknown"))
                ts = item.get("timestamp", "")
                lines.append(f"- **Aprendizado:** {learning}")
                lines.append(f"  - **Racional:** {rationale}")
                lines.append(f"  - **Origem:** `{origin}` | **Data:** {ts}")
            lines.append("")

        return "\n".join(lines)

    def render_session_history(self, history: List[Dict[str, Any]]) -> str:
        lines = [
            f"<!-- SESSION_HISTORY.md | Atualizado em: {get_timestamp()} -->",
            "# 📜 Histórico Cronológico de Sessões",
            "",
            format_visible_header(),
            ""
        ]
        for h in reversed(history):
            ts = h.get("timestamp", "")
            mac = h.get("machine_name", h.get("machine_id", "unknown"))
            task = h.get("task", h.get("summary", ""))
            p0 = h.get("next_step", h.get("p0", ""))
            lines.append(f"### 🕒 {ts} — `{mac}`")
            lines.append(f"- **Tarefa:** {task}")
            if p0:
                lines.append(f"- **Próximo Passo (P0):** `{p0}`")
            lines.append("")
        return "\n".join(lines)
