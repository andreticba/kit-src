#!/usr/bin/env python3
# kit_env_bootstrap.py | Vitalia Kit (Feature 009 — Fase 0 Hotfix)
# Atualizado em: 27-08-2026 19:34:16(GMT-04:00)
"""
Módulo Central de Bootstrap de Ambiente — Vitalia Kit

Responsabilidades:
1. Auto-descoberta do diretório raiz do projeto (workspace) subindo a árvore de pastas.
2. Parser nativo de .env (stdlib-only, sem exigência de python-dotenv no Python global).
3. Injeção dinâmica de site-packages do virtualenv (.venv / venv) em sys.path.
4. Diagnóstico de saúde de ambiente (presença de .env, .venv e conectividade com containers Docker).
5. Protocolo HITL com menu de 3 opções para tratamento de falhas de ambiente.

Referências: FR-003, FR-004, DEC-005, DEC-006
"""

import os
import re
import sys
import socket
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Any

# Injeção imediata do diretório de scripts do kit em sys.path ao importar o módulo
_KIT_SCRIPTS_DIR = str(Path(__file__).parent.resolve())
if _KIT_SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _KIT_SCRIPTS_DIR)



def find_project_root(start_path: Optional[Path] = None) -> Path:
    """
    Localiza a raiz do projeto subindo na hierarquia a partir de start_path ou cwd.
    Critérios de parada: presença de .git, .vitalia, .env, pyproject.toml ou setup.py.
    """
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path).resolve()

    current = start_path if start_path.is_dir() else start_path.parent
    indicators = [".git", ".vitalia", ".env", "pyproject.toml", "setup.py"]

    # Subir até encontrar um dos indicadores ou atingir a raiz do filesystem
    for _ in range(12):
        if any((current / ind).exists() for ind in indicators):
            return current
        if current.parent == current:
            break
        current = current.parent

    # Fallback: retornar o próprio start_path
    return start_path if start_path.is_dir() else start_path.parent


def load_dotenv_native(env_path: Path, override: bool = False) -> Dict[str, str]:
    """
    Parser nativo de arquivos .env (stdlib puro).
    Suporta:
    - Comentários (#) e linhas em branco
    - Aspas simples e duplas com escape
    - Prefixo opcional 'export '
    - Não sobrescreve variáveis existentes em os.environ a menos que override=True
    """
    loaded = {}
    if not env_path.exists() or not env_path.is_file():
        return loaded

    try:
        content = env_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return loaded

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].strip()

        if "=" not in line:
            continue

        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()

        # Tratar aspas e remover comentários inline
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        else:
            if "#" in val:
                val = val.split("#", 1)[0].strip()

        loaded[key] = val
        if override or key not in os.environ or not os.environ[key].strip() or os.environ[key].strip().startswith("#"):
            os.environ[key] = val

    return loaded


def inject_venv(project_root: Path) -> Tuple[bool, Optional[str]]:
    """
    Detecta pasta .venv ou venv no project_root, localiza a pasta site-packages
    e a injeta no início de sys.path.
    Retorna (sucesso, caminho_site_packages).
    """
    venv_names = [".venv", "venv"]
    for vname in venv_names:
        venv_dir = project_root / vname
        if not venv_dir.exists() or not venv_dir.is_dir():
            continue

        # Procurar diretórios site-packages dentro de lib/pythonX.Y/site-packages
        lib_dir = venv_dir / "lib"
        if lib_dir.exists():
            for py_dir in lib_dir.glob("python*"):
                sp = py_dir / "site-packages"
                if sp.exists() and sp.is_dir():
                    sp_str = str(sp.resolve())
                    if sp_str not in sys.path:
                        sys.path.insert(0, sp_str)
                    return True, sp_str

        # Caso alternativo (Windows ou layout plano)
        sp_win = venv_dir / "Lib" / "site-packages"
        if sp_win.exists() and sp_win.is_dir():
            sp_str = str(sp_win.resolve())
            if sp_str not in sys.path:
                sys.path.insert(0, sp_str)
            return True, sp_str

    return False, None


def _check_port_connectivity(host: str, port: int, timeout: float = 0.5) -> bool:
    """Verifica se uma porta TCP está ouvindo."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def check_environment_health(project_root: Path) -> Dict[str, Any]:
    """
    Diagnostica a saúde da infraestrutura do projeto:
    - Presença de .env e chaves essenciais (REDIS_URL, NO2_SERVER_IP)
    - Presença e injeção do .venv
    - Portas de containers locais (Redis: 6379, Postgres: 5432)
    """
    env_file = project_root / ".env"
    has_env = env_file.exists() and env_file.is_file()

    venv_ok, venv_path = inject_venv(project_root)

    # Port probes
    redis_port = int(os.environ.get("REDIS_PORT", "6379"))
    postgres_port = int(os.environ.get("POSTGRES_PORT", "5432"))

    redis_alive = _check_port_connectivity("127.0.0.1", redis_port)
    postgres_alive = _check_port_connectivity("127.0.0.1", postgres_port)

    # Redis probe via client se sys.path já injetado
    redis_client_ok = False
    redis_url = os.environ.get("REDIS_URL", "")
    if redis_alive and redis_url:
        try:
            import redis
            r = redis.from_url(redis_url, socket_connect_timeout=1.5)
            redis_client_ok = bool(r.ping())
        except Exception:
            redis_client_ok = False

    issues = []
    if not has_env:
        issues.append("Arquivo .env ausente na raiz do projeto")
    if not venv_ok:
        issues.append("Ambiente virtual (.venv/) não encontrado no projeto")
    if not redis_alive:
        issues.append(f"Container Redis inativo na porta {redis_port}")
    elif not redis_client_ok and redis_url:
        issues.append("Container Redis responde na porta, mas falhou autenticação/ping")

    status = "HEALTHY" if not issues else "DEGRADED"

    return {
        "status": status,
        "project_root": str(project_root),
        "has_env": has_env,
        "venv_ok": venv_ok,
        "venv_path": venv_path,
        "redis_port_open": redis_alive,
        "redis_client_ok": redis_client_ok,
        "postgres_port_open": postgres_alive,
        "issues": issues,
    }


def prompt_hitl_menu(health_report: Dict[str, Any]) -> str:
    """
    Formata o menu HITL de 3 opções quando o ambiente está degradado.
    Retorna a string formatada para exibição em log ou CLI.
    """
    issues_str = "\n".join(f"  ❌ {issue}" for issue in health_report.get("issues", []))
    menu = f"""
🛑 [VITALIA HITL: DIAGNÓSTICO DE AMBIENTE]
Foram detectadas inconsistências na infraestrutura do projeto:
{issues_str}

Opções disponíveis:
[1] Autocorreção Assistida:
    - Executar: docker compose up -d vitalia_redis
    - Ou inicializar .venv: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
[2] Prosseguir em Modo de Fallback (Degradação Graciosa):
    - Executa com persistência em arquivos Markdown/JSON locais, sem cache Redis.
[3] Parar Imediatamente:
    - Permite ao desenvolvedor inspecionar e ajustar as configurações manualmente.
"""
    return menu.strip()


def init(start_path: Optional[Path] = None, auto_load_env: bool = True) -> Dict[str, Any]:
    """
    Ponto de entrada padrão para qualquer script/hook do Vitalia Kit.
    Executa:
    1. Localização da raiz do projeto.
    2. Carregamento do .env do projeto no os.environ.
    3. Injeção do site-packages do .venv no sys.path.
    4. Diagnóstico de saúde.
    """
    root = find_project_root(start_path)

    if auto_load_env:
        env_file = root / ".env"
        if env_file.exists():
            load_dotenv_native(env_file, override=False)

    inject_venv(root)
    health = check_environment_health(root)
    return health


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Bootstrap Central de Ambiente — Vitalia Kit (v0.6.0)\n\n"
                    "Detecta a raiz do projeto, carrega .env nativamente, injeta o .venv\n"
                    "no sys.path e executa diagnósticos de infraestrutura.",
        epilog="Exemplos de uso:\n"
               "  python3 kit_env_bootstrap.py\n"
               "  python3 kit_env_bootstrap.py --cwd /caminho/do/projeto\n"
               "  python3 kit_env_bootstrap.py --menu\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--cwd", default=None, help="Diretório de início para busca da raiz do projeto")
    parser.add_argument("--menu", action="store_true", help="Exibir menu HITL se houver inconsistências")
    args = parser.parse_args()

    start = Path(args.cwd) if args.cwd else None
    health_info = init(start)

    print(f"[kit_env_bootstrap] Project Root: {health_info['project_root']}")
    print(f"[kit_env_bootstrap] Status: {health_info['status']}")
    print(f"[kit_env_bootstrap] .env: {'✅' if health_info['has_env'] else '❌'}")
    print(f"[kit_env_bootstrap] .venv: {'✅ (' + str(health_info['venv_path']) + ')' if health_info['venv_ok'] else '❌'}")
    print(f"[kit_env_bootstrap] Redis Client: {'✅ Online' if health_info['redis_client_ok'] else ('⚠️ Porta Aberta' if health_info['redis_port_open'] else '❌ Offline')}")

    if health_info["status"] != "HEALTHY" and args.menu:
        print("\n" + prompt_hitl_menu(health_info))
