#!/usr/bin/env python3
# sdd_judge.py | Vitalia SDD v0.6.0 | 02-11-2026 12:06(GMT-04:00)
# Propósito: Gatekeeper Constitucional em 6 Fases do Ciclo SDD (Shim CLI Fino)

import sys
from pathlib import Path

# Habilitar import de subpacotes a partir deste shim
_pkg_dir = Path(__file__).resolve().parent / "sdd_judge"
__path__ = [str(_pkg_dir)]

from sdd_judge import SDDJudge
from sdd_judge.cli import main

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n🛑 [SDDJudge] Operação cancelada pelo usuário (Ctrl+C).", file=sys.stderr)
        sys.exit(130)
