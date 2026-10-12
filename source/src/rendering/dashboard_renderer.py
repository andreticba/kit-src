#!/usr/bin/env python3
# dashboard_renderer.py | Vitalia Kit — Domínio RENDERING
# Atualizado em: 28-08-2026 09:00:00(GMT-04:00)
"""
Renderizador do Dashboard Master (README.md) — Vitalia Kit (Domínio RENDERING)

Responsabilidades:
1. Carregar estritamente o template canônico ~/.vitalia/config/templates/dashboard_template.md.
2. Injetar dados estruturados nos placeholders canônicos do template:
   - {timestamp}, {project_name}
   - {badge_status}, {badge_semaforo}, {badge_modo}, {badge_sync}, {badge_grounding}
   - {mermaid_content}, {shards_table}, {sessao_ativa}
   - {historico_sessoes}, {decisoes_arquiteturais}
   - {global_status}, {local_link}, {local_status}, {pending_badge}
3. Atender 100% ao critério de aceite visual validado em temp.md.
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
from core.utils import get_timestamp, format_visible_header


class DashboardRenderer:
    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.template_path = Path.home() / ".vitalia" / "config" / "templates" / "dashboard_template.md"

    def render(self, semaphore_data: Dict[str, Any], shards: List[Dict[str, Any]], history: List[Dict[str, Any]], decisions: List[Dict[str, Any]]) -> str:
        is_locked = semaphore_data.get("state") == "LOCKED"
        mode = "Integrado" if health.get("redis_client_ok", False) else "Standalone"
        ts = get_timestamp()
        project_name = kit_env_bootstrap.find_project_root().name

        # Badges individuais
        badge_status = '<img src="https://img.shields.io/badge/Status-Ativo-success?style=flat-square" alt="Status" />'
        
        if is_locked:
            sem_name = semaphore_data.get("machine_name", "machine")
            badge_semaforo = f'<img src="https://img.shields.io/badge/Semáforo-BLOQUEADO_{sem_name}-critical?style=flat-square" alt="Semáforo" />'
        else:
            badge_semaforo = '<img src="https://img.shields.io/badge/Semáforo-LIVRE-success?style=flat-square" alt="Semáforo" />'

        if mode == "Integrado":
            badge_modo = '<img src="https://img.shields.io/badge/Ambiente-Integrado-purple?style=flat-square" alt="Ambiente" />'
        else:
            badge_modo = '<img src="https://img.shields.io/badge/Ambiente-Standalone-blue?style=flat-square" alt="Ambiente" />'

        badge_sync = '<img src="https://img.shields.io/badge/Sync-GMT--04%3A00-informational?style=flat-square" alt="Sync" />'
        badge_grounding = '<img src="https://img.shields.io/badge/Grounding-Ativo-blueviolet?style=flat-square" alt="Grounding" />'

        # Mermaid
        mermaid_content = self._build_mermaid(shards)

        # Tabela de shards
        shards_table = self._build_shards_table(shards)

        # Sessão ativa
        sessao_ativa = self._build_active_session(shards, semaphore_data)

        # Histórico
        historico_sessoes = self._build_history(history)

        # Decisões
        decisoes_arquiteturais = self._build_decisions(decisions)

        # Grounding
        global_status = "✅ Ativo"
        local_link = "`grounding-domains-local.yaml`"
        local_status = "✅ Sincronizado"
        pending_badge = "`0 pendências`"

        template_str = self.template_path.read_text(encoding="utf-8") if self.template_path.exists() else ""
        if not template_str:
            template_str = "# Painel de Contexto\n{shards_table}"

        rendered = template_str.replace("{timestamp}", ts)
        rendered = rendered.replace("{project_name}", project_name)
        rendered = rendered.replace("{badge_status}", badge_status)
        rendered = rendered.replace("{badge_semaforo}", badge_semaforo)
        rendered = rendered.replace("{badge_modo}", badge_modo)
        rendered = rendered.replace("{badge_sync}", badge_sync)
        rendered = rendered.replace("{badge_grounding}", badge_grounding)
        rendered = rendered.replace("{mermaid_content}", mermaid_content)
        rendered = rendered.replace("{shards_table}", shards_table)
        rendered = rendered.replace("{sessao_ativa}", sessao_ativa)
        rendered = rendered.replace("{historico_sessoes}", historico_sessoes)
        rendered = rendered.replace("{decisoes_arquiteturais}", decisoes_arquiteturais)
        rendered = rendered.replace("{global_status}", global_status)
        rendered = rendered.replace("{local_link}", local_link)
        rendered = rendered.replace("{local_status}", local_status)
        rendered = rendered.replace("{pending_badge}", pending_badge)

        return rendered

    def _build_mermaid(self, shards: List[Dict[str, Any]]) -> str:
        lines = [
            '  Cloud(("☁️ Git Remoto / Hub"))'
        ]
        for s in shards:
            m_id = s.get("machine_id", "unknown")
            m_name = s.get("machine_name", "Máquina")
            task = s.get("current_task", "Livre")
            mode = s.get("mode", "Integrado")
            sync = s.get("last_sync", "")

            node_id = f"M_{m_id}"
            lines.append(f'  {node_id}["💻 {m_name}<br/><i>{task}</i><br/><code>{mode}</code>"]')
            lines.append(f'  {node_id} <-->|"{sync}"| Cloud')

            if mode == "Integrado":
                lines.append(f"  style {node_id} stroke:#8250df,stroke-width:2px,fill:#fbefff,color:#8250df")
            else:
                lines.append(f"  style {node_id} stroke:#0969da,stroke-width:2px,fill:#ddf4ff,color:#0969da")

        lines.append("  style Cloud stroke:#1a7f37,stroke-width:2px,fill:#dafbe1,color:#1a7f37")
        return "\n".join(lines)

    def _build_shards_table(self, shards: List[Dict[str, Any]]) -> str:
        rows = []
        for s in shards:
            m_id = s.get("machine_id", "")
            m_name = s.get("machine_name", "unknown")
            task = s.get("current_task", "")
            status = s.get("status", "Em Andamento")
            next_step = s.get("next_step", "")
            sync = s.get("last_sync", "")
            mode = s.get("mode", "Integrado")

            badge_mode = f'<img src="https://img.shields.io/badge/-{mode}-purple?style=flat-square" alt="{mode}" />' if mode == "Integrado" else f'<img src="https://img.shields.io/badge/-{mode}-blue?style=flat-square" alt="{mode}" />'

            rows.append(f"""    <tr>
      <td><strong>{m_name}</strong> (<code>{m_id}</code>)</td>
      <td>{task}</td>
      <td align="center">{badge_mode}</td>
      <td align="center"><span style="color:green;">●</span> {status}</td>
      <td>{sync}</td>
      <td><strong>{next_step}</strong></td>
    </tr>""")

        return "\n".join(rows)

    def _build_active_session(self, shards: List[Dict[str, Any]], sem: Dict[str, Any]) -> str:
        if not shards:
            return "> ℹ️ Nenhuma sessão ativa no momento."
        active = shards[0]
        return f"""- **Estação Ativa:** `{active.get('machine_name')}` (`{active.get('machine_id')}`)
- **Tarefa em Execução:** {active.get('current_task')}
- **🎯 Próximo Passo Prioritário (P0):** `{active.get('next_step')}`
- **Última Sincronização:** `{active.get('last_sync')}`"""

    def _build_history(self, history: List[Dict[str, Any]]) -> str:
        if not history:
            return "Nenhum histórico registrado até o momento."
        lines = [
            "| Data / Hora | Estação (ID) | Tarefa Executada | Próximo Passo (P0) |",
            "| :--- | :--- | :--- | :--- |"
        ]
        for h in reversed(history[-10:]):
            dt = h.get("timestamp", "")
            mac = f"{h.get('machine_name', 'machine')} ({h.get('machine_id', '')})"
            task = h.get("task", h.get("summary", ""))
            p0 = h.get("next_step", h.get("p0", "—"))
            lines.append(f"| {dt} | `{mac}` | {task} | `{p0}` |")
        return "\n".join(lines)

    def _build_decisions(self, decisions: List[Dict[str, Any]]) -> str:
        if not decisions:
            return "| — | Nenhuma decisão registrada. | — |"
        lines = []
        for d in reversed(decisions[-10:]):
            mac = f"{d.get('machine_id', 'andrenote')}"
            dec = f"**[{d.get('id', 'DEC')}]** `{d.get('category', '[ARCH]')}` {d.get('decision', '')}"
            rat = d.get('rationale', 'Registro defasado')
            lines.append(f"| `{mac}` | {dec} | {rat} |")
        return "\n".join(lines)
