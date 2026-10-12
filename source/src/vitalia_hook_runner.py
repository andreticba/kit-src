#!/usr/bin/env python3
# vitalia_hook_runner.py | Atualizado em: 21-09-2026 22:03:15(GMT-04:00)
# vitalia_hook_runner.py | Vitalia SDD v0.6.0
# Atualizado em: 03-09-2026 06:14(GMT-04:00)
"""
Vitalia Hook Runner — Ponte entre o Kit e as IDEs de IA.

Responsabilidades:
1. Parsear um arquivo .toml de workflow e emitir seu conteúdo como JSON no stdout.
2. Executar hooks [before]/[after] declarados no TOML (subprocessos Python/bash).
3. Substituir placeholders em templates de comando: {{cwd}}, {{VITALIA_KIT_DIR}}.
4. (§11) Construir e injetar o payload do Guardian no campo 'guardian_json'
   quando o TOML declara uma seção [guardian].

Uso:
  python3 vitalia_hook_runner.py <workflow.toml> [--phase before|after|none]

Fluxo para a IDE:
  SKILL.md instrui a IA → IA chama este script → script emite JSON →
  IA lê o campo 'prompt' (e 'guardian_json' se presente) → IA executa.

Referências: US3, T008–T011, §11 da spec 001-guardian-kit-bootstrap
"""

import os
import sys
import argparse
import json
import subprocess
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print("Erro: Este script requer Python 3.11+ (tomllib) ou o pacote 'tomli'.", file=sys.stderr)
        sys.exit(1)


# ─── RESOLUÇÃO DO KIT DIR ────────────────────────────────────────────────────

def resolve_kit_dir() -> str:
    """
    Descobre o diretório raiz do Kit Global em ordem de precedência:
    1. Variável de ambiente VITALIA_KIT_DIR (permite override em testes).
    2. ~/.vitalia/ (caminho padrão de produção).

    Retorna string com o caminho absoluto, sem barra final.
    """
    env_val = os.environ.get("VITALIA_KIT_DIR", "").strip()
    if env_val:
        return env_val.rstrip("/")
    return str(Path.home() / ".vitalia")


# ─── §11 — GUARDIAN PAYLOAD BUILDER ─────────────────────────────────────────

def _build_guardian_payload(guardian_config: dict, workflow_name: str, cwd: str, user_args: str = "") -> dict:
    """
    §11 — Constrói o payload do Guardian chamando GuardianContextV2.

    Estratégia:
    - Injeta o diretório de scripts do kit no sys.path para importar guardian_context.
    - Instancia GuardianContextV2 com as configurações do TOML.
    - Chama build_payload() e retorna o dict resultante.
    - Em caso de qualquer falha, retorna um dict de erro em vez de abortar — o
      hook_runner nunca deve impedir a IA de receber o JSON do TOML.

    Args:
        guardian_config: Conteúdo da seção [guardian] do TOML.
        workflow_name:   Nome do workflow (basename do arquivo .toml sem extensão).
        cwd:             Diretório de trabalho atual.
        user_args:       Input textual do usuário capturado via --args (C1: popula
                         session_context.user_input no guardian_json).

    Returns:
        Dict com o payload ou dict com chave 'error' descrevendo a falha.
    """
    kit_dir = resolve_kit_dir()
    # Adiciona kit/src/ ao path para permitir importação do guardian_context
    kit_src = str(Path(kit_dir) / "src")
    kit_scripts = str(Path(kit_dir) / "scripts")  # compatibilidade com legado
    for p in [kit_src, kit_scripts]:
        if p not in sys.path:
            sys.path.insert(0, p)

    try:
        from hooks.guardian_context import GuardianContextV2  # type: ignore
        guardian = GuardianContextV2(
            workflow_name=workflow_name,
            guardian_config=guardian_config,
            cwd=Path(cwd),
            user_args=user_args,  # C1: repassa input do usuário
        )
        return guardian.build_payload()
    except ImportError as e:
        msg = f"[Guardian] Módulo guardian_context não encontrado em {kit_src}: {e}"
        print(msg, file=sys.stderr)
        return {"error": msg, "kit_src_tried": kit_src}
    except Exception as e:
        msg = f"[Guardian] Falha ao construir payload: {type(e).__name__}: {e}"
        print(msg, file=sys.stderr)
        return {"error": msg}


# ─── SUBSTITUIÇÃO DE PLACEHOLDERS ────────────────────────────────────────────

def resolve_placeholders(cmd_template: str, cwd: str, kit_dir: str) -> str:
    """
    Substitui todos os placeholders suportados em um template de comando.

    Placeholders:
    - {{cwd}}             → diretório de trabalho atual
    - {{VITALIA_KIT_DIR}} → caminho do Kit Global (~/.vitalia/ ou env override)
    - {{FEATURE_DIR}}     → feature ativa lida de .vitalia/feature.json

    Args:
        cmd_template: String do comando com zero ou mais placeholders.
        cwd:          Diretório atual (os.getcwd()).
        kit_dir:      Caminho do Kit Global (resolve_kit_dir()).

    Returns:
        Comando com todos os placeholders substituídos.
    """
    cmd = cmd_template
    cmd = cmd.replace("{{cwd}}", cwd)
    cmd = cmd.replace("{{VITALIA_KIT_DIR}}", kit_dir)

    # {{FEATURE_DIR}} — lê a feature ativa de .vitalia/feature.json (se existir)
    if "{{FEATURE_DIR}}" in cmd:
        feature_json = Path(cwd) / ".vitalia" / "feature.json"
        feature_dir = ""
        if feature_json.exists():
            try:
                with open(feature_json, encoding="utf-8") as f:
                    feature_data = json.load(f)
                feature_dir = feature_data.get("feature_directory", "")
            except (json.JSONDecodeError, OSError):
                pass
        cmd = cmd.replace("{{FEATURE_DIR}}", feature_dir)

    return cmd


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Vitalia Hook Runner — Ponte Kit ↔ IDE",
        epilog="""Exemplos:
  # Emitir JSON do workflow de sessão (sem executar hooks):
  python3 vitalia_hook_runner.py ~/.vitalia/extensions/session-start.toml

  # Executar hooks before e emitir JSON com guardian_json:
  python3 vitalia_hook_runner.py ~/.vitalia/extensions/brainstorming.toml --phase before --args "quero criar um tracker de treinos"
        """
    )
    parser.add_argument("file", help="Caminho para o arquivo .toml do workflow")
    parser.add_argument(
        "--phase",
        choices=["before", "after", "none"],
        default="none",
        help="Fase dos hooks a executar. 'none' apenas emite o JSON sem executar hooks."
    )

    parser.add_argument(
        "--args",
        default="",
        help="Input textual do usuário (C1: injetado em guardian_json.session_context.user_input)."
    )

    args = parser.parse_args()

    # ── 1. Verificar existência do arquivo TOML ──────────────────────────────
    if not os.path.exists(args.file):
        print(f"Erro: Arquivo não encontrado: {args.file}", file=sys.stderr)
        sys.exit(1)

    # ── 2. Parsear o TOML ────────────────────────────────────────────────────
    try:
        with open(args.file, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        print(f"Erro ao fazer parse do TOML: {e}", file=sys.stderr)
        sys.exit(1)

    # ── 3. Preparar variáveis de contexto ────────────────────────────────────
    cwd = os.getcwd()
    kit_dir = resolve_kit_dir()

    # Nome do workflow = basename sem extensão (ex: "brainstorming")
    workflow_name = Path(args.file).stem

    # ── 4. Executar hooks da fase solicitada ─────────────────────────────────
    if args.phase in ["before", "after"]:
        hooks = data.get("hooks", {}).get(args.phase, [])
        if isinstance(hooks, str):
            # TOML pode declarar hook como string simples ou lista
            hooks = [hooks]

        for cmd_template in hooks:
            # Substituir placeholders antes de executar
            cmd = resolve_placeholders(cmd_template, cwd, kit_dir)
            print(f"[Hook Runner] Executando hook ({args.phase}): {cmd}", file=sys.stderr)

            # FR-001 — Roteamento Híbrido: construir cópia isolada do ambiente para o subprocess.
            # Resolve race condition de os.environ global em execuções concorrentes de fases SDD.
            env_copia = os.environ.copy()
            model_profile = data.get("meta", {}).get("model_profile", "")
            if model_profile == "pro":
                gemini_model = os.environ.get("GEMINI_MODEL_PRO", "gemini-3.1-pro-preview")
                env_copia["GEMINI_MODEL"] = gemini_model
                print(f"[Hook Runner] 🤖 model_profile=pro → GEMINI_MODEL={gemini_model}", file=sys.stderr)
            elif model_profile == "flash":
                gemini_model = os.environ.get("GEMINI_MODEL_FLASH", "gemini-3.6-flash")
                env_copia["GEMINI_MODEL"] = gemini_model
                print(f"[Hook Runner] ⚡ model_profile=flash → GEMINI_MODEL={gemini_model}", file=sys.stderr)

            try:
                # stdout do subprocesso vai para stderr para não contaminar o JSON de saída
                subprocess.run(cmd, shell=True, check=True, stdout=sys.stderr, stderr=sys.stderr, env=env_copia)
            except subprocess.CalledProcessError as e:
                print(f"[Hook Runner] ❌ Hook falhou com código {e.returncode}: {cmd}", file=sys.stderr)
                # FR-002 — Trava STOP: emitir Stub de erro no stdout antes de encerrar.
                # A IDE de IA lê este JSON e deve parar imediatamente ao ver status="error".
                error_stub = {
                    "status": "error",
                    "workflow": workflow_name,
                    "hook_failed": cmd,
                    "exit_code": e.returncode,
                    "message": f"Hook '{args.phase}' falhou com código {e.returncode}. Ambiente não confiável.",
                    "action_required": "Reportar este erro ao usuário e NÃO prosseguir com o workflow."
                }
                print(json.dumps(error_stub, indent=2, ensure_ascii=False))
                sys.exit(e.returncode)

    # ── 5. §11 — Injetar guardian_json se TOML tem seção [guardian] ──────────
    # A seção [guardian] sinaliza que este workflow quer contexto do Guardian.
    # O payload é construído e adicionado ao dict 'data' antes do json.dumps().
    guardian_config = data.get("guardian", {})
    if guardian_config:
        print(f"[Hook Runner] §11 — Construindo payload Guardian para '{workflow_name}'...", file=sys.stderr)
        guardian_payload = _build_guardian_payload(
            guardian_config, workflow_name, cwd,
            user_args=args.args  # C1: propaga --args para session_context.user_input
        )
        if isinstance(guardian_payload, dict) and "error" not in guardian_payload:
            try:
                from maintenance.tmp_cleanup import TmpCleanup
                guardian_payload["tmp_cleanup_matrix"] = TmpCleanup().generate_matrix_dict()
            except Exception as e:
                print(f"[Hook Runner] ⚠️ Alerta ao gerar tmp_cleanup_matrix: {e}", file=sys.stderr)

        data["guardian_json"] = guardian_payload
        tokens = guardian_payload.get("estimated_tokens", "?")
        print(f"[Hook Runner] §11 — Payload Guardian pronto (~{tokens} tokens).", file=sys.stderr)

    # ── 6. Saída passiva para consumo da IA (Refatorado para Context Lifting) ──
    # Geração do timestamp higienizado para filesystem
    VITALIA_TIMEZONE = timezone(timedelta(hours=-4))
    safe_ts = datetime.now(VITALIA_TIMEZONE).strftime("%Y%m%d_%H%M%S")
    
    # Resolução do Session ID com fallback temporal
    session_id = os.environ.get("VITALIA_SESSION_ID", safe_ts)
    
    # Hash do PID para evitar concorrência no disco
    pid_hash = hashlib.sha256(f"{os.getpid()}_{workflow_name}".encode()).hexdigest()[:12]
    
    # Caminho do arquivo referencial no disco
    file_name = f"{workflow_name}_{session_id}_{pid_hash}.json"
    file_path = Path(kit_dir) / "tmp" / file_name
    
    # Garantir que o diretório tmp/ existe
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Persistir o dicionário data completo no disco (Context Lifting)
    file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    
    # Disparar evento no Redis (Restaurando a telemetria do GuardianContextV2 bypassado)
    if guardian_config:
        try:
            import redis
            try:
                from dotenv import load_dotenv
                load_dotenv(Path(cwd) / ".env")
            except ImportError:
                pass
            
            r_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
            client = redis.from_url(r_url, socket_connect_timeout=1)
            
            profile_name = guardian_config.get("guardian_profile", "unknown_profile")
            tokens_val = str(data.get("guardian_json", {}).get("estimated_tokens", 0))
            budget_val = str(data.get("guardian_json", {}).get("token_budget", 0))
            
            client.xadd("vitalia:telemetry_events", {
                "event": "context_compiled",
                "workflow": workflow_name,
                "profile": profile_name,
                "tokens": tokens_val,
                "budget": budget_val,
                "transport": "file_stub"
            })
        except Exception as e:
            # Tolerância a falhas na telemetria
            print(f"[Hook Runner] ⚠️ Falha na telemetria Redis: {e}", file=sys.stderr)

    # Construir e emitir o Stub JSON
    stub = {
        "status": "ready",
        "workflow": workflow_name,
        "workflow_context_file": str(file_path),
        "action_required": "USE a ferramenta view_file para ler este arquivo referenciado acima e carregar o contexto ('prompt') e regras ('guardian_json')."
    }
    
    # IMPORTANTE: Todo o stdout é JSON puro. Logs vão para stderr.
    print(json.dumps(stub, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
