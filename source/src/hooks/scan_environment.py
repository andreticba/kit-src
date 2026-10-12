#!/usr/bin/env python3
# scan_environment.py | Vitalia SDD v0.6.0 | 19-09-2026 07:30(GMT-04:00)
"""
Executa a varredura do ambiente (via kit_env_bootstrap) e retorna o status em JSON.

Exit codes:
  0 — ambiente HEALTHY ou DEGRADED (Redis/venv ausentes são condições toleráveis)
  1 — ambiente CRITICAL: .env ausente (sem configuração básica, impossível operar)
"""
import sys
import json
import argparse
from pathlib import Path
_scripts_root = str(Path(__file__).resolve().parent.parent)
if _scripts_root not in sys.path:
    sys.path.insert(0, _scripts_root)
import kit_env_bootstrap

def main():
    parser = argparse.ArgumentParser(
        description="Varredura de Ambiente e Diagnóstico — Vitalia Kit (v0.6.0)\n\n"
                    "Executa a inspeção do ambiente do projeto via kit_env_bootstrap\n"
                    "e emite o relatório de saúde estruturado em formato JSON.",
        epilog="Exemplos de uso:\n"
               "  python3 scan_environment.py\n"
               "  python3 scan_environment.py --help\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--cwd", type=str, default=None, help="Diretório de trabalho alvo para varredura do ambiente.")
    args = parser.parse_args()

    health = kit_env_bootstrap.init()
    print(json.dumps(health, indent=2, ensure_ascii=False))

    if not health.get("has_env", False):
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
