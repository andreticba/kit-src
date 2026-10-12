#!/usr/bin/env python3
# guardian_context.py | Vitalia SDD v0.6.0 — Domínio HOOKS
# Atualizado em: 03-09-2026 06:15(GMT-04:00)
"""
Guardião de Contexto Polimórfico e Compilador de Context Engineering — Vitalia SDD v0.6.0

Suporta:
- Carregamento dinâmico de múltiplas fontes YAML por schema_type de profiles/.
- Dois formatos de constitution: legado (modules[]) e Dual-Index (domain_index + principles).
- Poda semântica com cotas calibradas (source_weights).
- Fallback explícito para constitution_data.yaml legado com WARNING no stderr.
- Emissão de guardian_advisory para TOMLs sem guardian_profile dedicado.

Referências: US2, US4, T012, T013 — spec 001-guardian-kit-bootstrap
"""

import os
import sys
import re
import json
import shlex
import argparse
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

_scripts_root = str(Path(__file__).resolve().parent.parent)
if _scripts_root not in sys.path:
    sys.path.insert(0, _scripts_root)

import kit_env_bootstrap
health = kit_env_bootstrap.init()
from core.utils import get_timestamp, format_visible_header

try:
    import yaml
except ImportError:
    yaml = None


# ─── ADAPTADORES POLIMÓRFICOS ──────────────────────────────────────────────

class BaseAdapter:
    def prune(self, data: Dict[str, Any], profile: Dict[str, Any], token_limit: int) -> Dict[str, Any]:
        return data


class ConstitutionAdapter(BaseAdapter):
    """
    Adapter legado: suporta constitution_data.yaml com estrutura modules[].
    Mantido para compatibilidade retroativa. Novo formato: ConstitutionAdapterV2.
    """
    def prune(self, data: Dict[str, Any], profile: Dict[str, Any], token_limit: int) -> Dict[str, Any]:
        const_cfg = profile.get("constitution", {})
        allowed_domains = set(const_cfg.get("domains", []))
        severity_filter = set(const_cfg.get("severity_filter", ["BLOCKING"]))
        exclude_principles = set(const_cfg.get("principles_exclude", []))
        include_principles = set(const_cfg.get("principles_include", []))

        pruned_modules = []
        for mod in data.get("modules", []):
            if allowed_domains and mod.get("id") not in allowed_domains:
                continue
            pruned_principles = []
            for p in mod.get("principles", []):
                p_id = p.get("id")
                if exclude_principles and p_id in exclude_principles:
                    continue
                if include_principles and p_id not in include_principles:
                    continue
                if severity_filter and p.get("severity") not in severity_filter:
                    continue
                pruned_principles.append(p)
            if pruned_principles:
                mod_copy = dict(mod)
                mod_copy["principles"] = pruned_principles
                pruned_modules.append(mod_copy)

        return {
            "schema_type": "constitution",
            "schema_version": data.get("schema_version", "0.5.0"),
            "modules": pruned_modules
        }


class ConstitutionAdapterV2(BaseAdapter):
    """
    T013 — Adapter para constitution.yaml no formato Dual-Index (Opção D, v0.6.0).

    Lookup O(1) por domain_id via domain_index:
      1. Filtrar domain_index pelos domínios solicitados no profile.
      2. Coletar os principle_ids correspondentes.
      3. Buscar cada princípio diretamente em principles[id].
      4. Aplicar filtro de severity.

    Isso substitui a iteração O(n*m) do adapter legado.
    """
    def prune(self, data: Dict[str, Any], profile: Dict[str, Any], token_limit: int) -> Dict[str, Any]:
        const_cfg = profile.get("constitution", {})
        # Domínios solicitados pelo guardian_profile (lista vazia = todos)
        allowed_domains = set(const_cfg.get("domains", []))
        severity_filter = set(const_cfg.get("severity_filter", ["BLOCKING", "WARNING"]))
        exclude_principles = set(const_cfg.get("principles_exclude", []))
        include_principles = set(const_cfg.get("principles_include", []))

        domain_index: Dict[str, List[str]] = data.get("domain_index", {})
        all_principles: Dict[str, Any] = data.get("principles", {})

        # Passo 1 — coletar IDs dos domínios permitidos (O(1) por domínio)
        target_ids: List[str] = []
        for domain_id, principle_ids in domain_index.items():
            if allowed_domains and domain_id not in allowed_domains:
                continue  # Domínio não solicitado — pular
            target_ids.extend(principle_ids)

        # Passo 2 — filtrar por severity e include/exclude lists
        selected: Dict[str, Any] = {}
        for pid in target_ids:
            if exclude_principles and pid in exclude_principles:
                continue
            if include_principles and pid not in include_principles:
                continue
            principle = all_principles.get(pid)
            if not principle:
                continue  # ID no índice mas sem definição — skip defensivo
            if severity_filter and principle.get("severity") not in severity_filter:
                continue
            selected[pid] = principle

        # Passo 3 — reconstruir domain_index filtrado (apenas domínios com princípios selecionados)
        filtered_index: Dict[str, List[str]] = {}
        for domain_id, principle_ids in domain_index.items():
            kept = [pid for pid in principle_ids if pid in selected]
            if kept:
                filtered_index[domain_id] = kept

        return {
            "schema_type": "constitution",
            "schema_version": data.get("schema_version", "0.6.0"),
            "domain_index": filtered_index,
            "principles": selected,
        }


class RoutingTableAdapter(BaseAdapter):
    def prune(self, data: Dict[str, Any], profile: Dict[str, Any], token_limit: int) -> Dict[str, Any]:
        agents = data.get("agents", [])
        return {
            "schema_type": "routing_table",
            "agents": agents
        }


class AgentsCatalogAdapter(BaseAdapter):
    def prune(self, data: Dict[str, Any], profile: Dict[str, Any], token_limit: int) -> Dict[str, Any]:
        agents = data.get("agents", [])
        return {
            "schema_type": "agents_catalog",
            "agents": agents
        }


# C6/C7: BrainstormingIntentsAdapter
# Carrega brainstorming_intents.yaml e o torna disponível no payload do Guardian.
# Permite que vitalia-route e brainstorming consumam o catálogo de intents via yaml_sources.
class BrainstormingIntentsAdapter(BaseAdapter):
    def prune(self, data: Dict[str, Any], profile: Dict[str, Any], token_limit: int) -> Dict[str, Any]:
        # Repassa o catálogo de domínios intacto (C8: apenas dados, sem comportamento)
        return {
            "schema_type": "brainstorming_intents",
            "schema_version": data.get("schema_version", "0.6.0"),
            "domains": data.get("domains", {}),
        }


ADAPTERS = {
    # constitution: usa V2 (Dual-Index) para novos arquivos em profiles/
    # Se o arquivo carregado for legado (tem 'modules'), load_yaml() já detecta e usa V1.
    "constitution": ConstitutionAdapterV2(),
    "constitution_legacy": ConstitutionAdapter(),  # Fallback explícito para modules[]
    "routing_table": RoutingTableAdapter(),
    "agents_catalog": AgentsCatalogAdapter(),
    "brainstorming_intents": BrainstormingIntentsAdapter(),  # C6/C7
}


# ─── GUARDIAN CONTEXT ENGINE V0.0.1 ─────────────────────────────────────────

class GuardianContextV2:
    def __init__(self, workflow_name: str, guardian_config: Dict[str, Any] = None,
                 session_dir: Path = None, cwd: Path = None, user_args: str = ""):
        self.workflow_name = workflow_name
        self.guardian_config = guardian_config or {}
        self.cwd = cwd or Path.cwd()
        self.session_dir = session_dir or (self.cwd / ".vitalia" / "memory" / "session")
        self.kit_root = Path.home() / ".vitalia"
        self.profiles_dir = self.kit_root / "profiles"
        self.tmp_dir = self.kit_root / "tmp"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.advisory = None
        # C1: input do usuário capturado via --args pelo hook_runner
        self.user_args = user_args

    def _estimate_tokens(self, obj: Any) -> int:
        text = json.dumps(obj, ensure_ascii=False)
        return int(len(text.split()) * 1.3)

    def load_yaml(self, name: str) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        T012 — Carrega um arquivo YAML de profiles/ pelo nome (sem extensão).

        Ordem de resolução:
        1. profiles/ no kit instalado (~/.vitalia/profiles/<name>.yaml)
        3. Fallback legado APENAS para 'constitution' (rules/always-on/constitution_data.yaml)
           com WARNING explícito no stderr — NÃO é silencioso.

        Args:
            name: Nome do arquivo sem extensão. Ex: 'constitution', 'routing_table'.

        Returns:
            Tupla (data_dict, schema_type). schema_type pode ser:
            - 'constitution' para Dual-Index (domain_index + principles)
            - 'constitution_legacy' para formato legado (modules[])
            - o valor de data['schema_type'] ou o name como fallback
        """
        if not yaml:
            return None, "yaml_module_missing"

        # Caminho 1: profiles/ no kit global instalado
        path = self.profiles_dir / f"{name}.yaml"

        # Caminho 2: profiles/ relativo ao cwd do projeto (útil em dev)
        cwd_profiles = self.cwd / "profiles" / f"{name}.yaml"

        target_path = None
        if path.exists():
            target_path = path
        elif cwd_profiles.exists():
            target_path = cwd_profiles
            print(f"[Guardian] INFO: Usando profiles/ do projeto local: {cwd_profiles}", file=sys.stderr)

        if target_path:
            data = yaml.safe_load(target_path.read_text(encoding="utf-8"))
            # Detectar formato: Dual-Index tem 'domain_index', legado tem 'modules'
            if "domain_index" in data:
                schema_type = "constitution"  # ConstitutionAdapterV2
            elif "modules" in data:
                schema_type = "constitution_legacy"  # ConstitutionAdapter (legado)
            else:
                schema_type = data.get("schema_type", name)
            return data, schema_type

        # Caminho 3: Fallback para profiles/constitution.yaml (v0.6.0)
        # NOTA: O path legado rules/always-on/constitution_data.yaml foi removido em v0.6.0.
        # Este fallback aponta diretamente para profiles/ — load_yaml() detecta o formato
        # via 'domain_index' e seleciona ConstitutionAdapterV2 automaticamente.
        if name == "constitution":
            fallback = self.profiles_dir / "constitution.yaml"
            if fallback.exists():
                print(
                    f"[Guardian] INFO: profiles/{name}.yaml não encontrado via caminho primário. "
                    f"Usando fallback: {fallback}",
                    file=sys.stderr
                )
                data = yaml.safe_load(fallback.read_text(encoding="utf-8"))
                schema_type = "constitution" if "domain_index" in data else "constitution_legacy"
                return data, schema_type

        print(f"[Guardian] WARNING: {name}.yaml não encontrado em profiles/ ({self.profiles_dir})", file=sys.stderr)
        return None, "file_not_found"

    def resolve_profile(self) -> Dict[str, Any]:
        profile_name = self.guardian_config.get("guardian_profile")
        if profile_name:
            p_data, _ = self.load_yaml(profile_name)
            if p_data:
                return p_data

        # Verificar se profile foi passado inline
        inline_gate = self.guardian_config.get("gate")
        if inline_gate:
            return {
                "schema_type": "guardian_profile",
                "tokens": {"total_budget": inline_gate.get("token_budget", 400), "source_weights": inline_gate.get("source_weights", {})},
                "constitution": {"domains": inline_gate.get("domains", []), "severity_filter": inline_gate.get("severity_filter", ["BLOCKING"])}
            }

        # Fallback para perfil default do workflow
        p_data, _ = self.load_yaml(f"gp_{self.workflow_name}")
        if p_data:
            return p_data

        self.advisory = f"[GUARDIAN ADVISORY: Workflow '{self.workflow_name}' operando sem guardian_profile dedicado — usando fallback completo.]"
        return {
            "schema_type": "guardian_profile",
            "tokens": {"total_budget": 500, "source_weights": {"constitution": 1.0}},
            "constitution": {"domains": [], "severity_filter": ["BLOCKING", "WARNING"]}
        }

    def load_session_context(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        sess_cfg = profile.get("session_context", {})
        session_ctx = {}

        if sess_cfg.get("include_p0", True):
            st_file = self.session_dir / "SESSION_STATE.md"
            if st_file.exists():
                lines = st_file.read_text(encoding="utf-8").splitlines()
                p0_lines = [l for l in lines if "P0" in l or "Próximo Passo" in l or "Next Step" in l]
                session_ctx["p0"] = p0_lines[0].strip() if p0_lines else "Dar continuidade à implementação planejada."
            else:
                session_ctx["p0"] = "Inicialização de sessão."

        feat_file = self.cwd / ".vitalia" / "feature.json"
        if sess_cfg.get("include_active_feature", True) and feat_file.exists():
            try:
                f_data = json.loads(feat_file.read_text(encoding="utf-8"))
                session_ctx["active_feature"] = f_data.get("feature_directory") or f_data.get("active_feature") or "Geral"
            except Exception:
                session_ctx["active_feature"] = "Geral"

        if sess_cfg.get("include_agents_queue", True):
            session_ctx["agents_queue"] = {
                "design-thinking": {"pending_tasks": 0},
                "literature-curator": {"pending_tasks": 0},
                "medical-gate": {"pending_tasks": 0}
            }

        return session_ctx

    # -------------------------------------------------------------------------
    # C3: _load_historical_context
    # Lê as últimas N entradas de decisions.jsonl e learnings.jsonl.
    # Retorna listas vazias sem exceção se os arquivos não existirem.
    # Fonte de verdade: data/*.jsonl (não os *.md).
    # -------------------------------------------------------------------------
    def _load_historical_context(self, n: int = 5) -> Dict[str, Any]:
        result: Dict[str, Any] = {"context_decisions": [], "context_learnings": []}
        for key, filename in [("context_decisions", "decisions.jsonl"),
                              ("context_learnings", "learnings.jsonl")]:
            for base_dir in [self.session_dir / "data", self.cwd / "data",
                             self.cwd / ".vitalia" / "data"]:
                jsonl_path = base_dir / filename
                if jsonl_path.exists():
                    try:
                        lines = jsonl_path.read_text(encoding="utf-8").splitlines()
                        entries = []
                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                entries.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass
                        # Ordenar por timestamp e pegar os N mais recentes
                        entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                        result[key] = entries[:n]
                    except Exception:
                        pass
                    break  # Encontrou o arquivo — não procurar nos outros diretórios
        return result

    # -------------------------------------------------------------------------
    # C2: _load_env_summary
    # Invoca scan_environment se disponível; fallback para {} sem exceção.
    # -------------------------------------------------------------------------
    def _load_env_summary(self) -> Dict[str, Any]:
        try:
            import importlib, sys as _sys
            kit_src = str(self.kit_root / "src")
            if kit_src not in _sys.path:
                _sys.path.insert(0, kit_src)
            scan_mod = importlib.import_module("hooks.scan_environment")
            if hasattr(scan_mod, "check_environment_health"):
                return scan_mod.check_environment_health(str(self.cwd)) or {}
        except Exception:
            pass
        return {}

    def build_payload(self) -> Dict[str, Any]:
        profile = self.resolve_profile()
        yaml_sources = self.guardian_config.get("yaml_sources", ["constitution"])
        if not yaml_sources:
            yaml_sources = ["constitution"]

        tokens_cfg = profile.get("tokens", {})
        total_budget = tokens_cfg.get("total_budget", 500)
        weights = tokens_cfg.get("source_weights", {})

        payload_sources = {}
        for src_name in yaml_sources:
            raw_data, stype = self.load_yaml(src_name)
            if not raw_data:
                continue
            
            adapter = ADAPTERS.get(stype, BaseAdapter())
            src_weight = weights.get(src_name, 1.0 / len(yaml_sources))
            src_token_limit = int(total_budget * src_weight)
            
            pruned_data = adapter.prune(raw_data, profile, src_token_limit)
            payload_sources[src_name] = pruned_data

        # Inicializar session_ctx via load_session_context (FIX: C1 — variável nunca era definida aqui)
        session_ctx = self.load_session_context(profile)

        # C1: injetar user_input no session_context
        if self.user_args:
            session_ctx["user_input"] = self.user_args

        # C2: env_summary — estado de infraestrutura (Redis, venv, git, Ollama)
        env_summary = self._load_env_summary()

        # C3: histórico de decisions e learnings
        historical = self._load_historical_context(n=5)

        result_payload = {
            "schema_version": "0.6.0",  # T013: atualizado para Vitalia SDD v0.6.0
            "workflow": self.workflow_name,
            "timestamp": get_timestamp(),
            "sources": payload_sources,
            "session_context": session_ctx,
            "env_summary": env_summary,               # C2
            "context_decisions": historical["context_decisions"],  # C3
            "context_learnings": historical["context_learnings"],  # C3
        }

        if self.advisory:
            result_payload["guardian_advisory"] = self.advisory

        total_est = self._estimate_tokens(result_payload)
        result_payload["estimated_tokens"] = total_est
        result_payload["token_budget"] = total_budget

        return result_payload

    def export_and_publish(self) -> Path:
        payload = self.build_payload()
        pid_hash = hashlib.sha256(f"{os.getpid()}_{self.workflow_name}".encode()).hexdigest()[:12]
        out_file = self.tmp_dir / f"guardian_{pid_hash}.json"
        out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        # Publicar evento no Redis caso disponível
        try:
            import redis
            r_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
            client = redis.from_url(r_url, socket_connect_timeout=1)
            
            profile_name = self.guardian_config.get("guardian_profile", "unknown_profile")
            
            client.xadd("vitalia:telemetry_events", {
                "event": "context_compiled",
                "workflow": self.workflow_name,
                "profile": profile_name,
                "tokens": str(payload.get("estimated_tokens", 0)),
                "budget": str(payload.get("token_budget", 0))
            })
        except Exception:
            pass

        return out_file


def main():
    parser = argparse.ArgumentParser(
        description="Guardião de Contexto Polimórfico e Compilador — Vitalia SDD (v0.6.0)\n\n"
                    "Carrega profiles/ e constitution.yaml, realiza a poda semântica e\n"
                    "compila o payload guardian_json para injeção nos workflows.",
        epilog="Exemplos de uso:\n"
               "  python3 guardian_context.py --workflow session-start\n"
               "  python3 guardian_context.py --workflow brainstorming --args 'nova feature'\n"
               "  python3 guardian_context.py --workflow spec-plan --guardian-json '{\"yaml_sources\": [\"constitution\"]}'\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--workflow", default="default", help="Nome do workflow ativo")
    parser.add_argument("--guardian-json", default="{}", help="Configuração JSON serializada da seção [guardian] do TOML")
    parser.add_argument("--session-dir", default=None, help="Caminho do diretório de sessão")
    parser.add_argument("--cwd", default=None, help="Caminho da raiz do projeto")
    parser.add_argument("--args", default="", help="Argumentos do usuário")

    args = parser.parse_args()

    g_config = {}
    if args.guardian_json and args.guardian_json != "{}":
        try:
            g_config = json.loads(args.guardian_json)
        except Exception:
            pass

    cwd_path = Path(args.cwd) if args.cwd else Path.cwd()
    sess_path = Path(args.session_dir) if args.session_dir else (cwd_path / ".vitalia" / "memory" / "session")

    guardian = GuardianContextV2(
        workflow_name=args.workflow,
        guardian_config=g_config,
        session_dir=sess_path,
        cwd=cwd_path
    )

    out_file = guardian.export_and_publish()
    print(f"✅ Guardian V2 exportado para {out_file}")
    if guardian.advisory:
        print(f"⚠️ {guardian.advisory}")


if __name__ == "__main__":
    main()
