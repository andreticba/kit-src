#!/usr/bin/env python3
# tmp_cleanup.py | Vitalia Kit — Domínio MAINTENANCE
# Atualizado em: 19-09-2026 07:30:00(GMT-04:00)
"""
Limpeza Interativa de Arquivos Temporários — Vitalia Kit (Domínio MAINTENANCE)

Verifica a matriz de arquivos temporários em ~/.vitalia/tmp/ agrupados por data,
emite a matriz em JSON conforme tmp_cleanup_matrix.schema.json e gerencia o expurgo
com transferência para a quarentena (~/.vitalia/tmp/.trash/).
"""

import os
import sys
import time
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import argparse

_scripts_root = str(Path(__file__).resolve().parent.parent)
if _scripts_root not in sys.path:
    sys.path.insert(0, _scripts_root)

import kit_env_bootstrap
health = kit_env_bootstrap.init()
from core.utils import get_current_datetime, get_timestamp

try:
    import jsonschema
except ImportError:
    jsonschema = None


def format_bytes(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


class TmpCleanup:
    def __init__(self, tmp_dir: Optional[Path] = None):
        self.tmp_dir = tmp_dir or (Path.home() / ".vitalia" / "tmp")

    def get_trash_dir(self) -> Path:
        trash = self.tmp_dir / ".trash"
        trash.mkdir(parents=True, exist_ok=True)
        return trash

    def scan_by_date(self) -> Dict[str, List[Path]]:
        if not self.tmp_dir.exists():
            return {}

        grouped: Dict[str, List[Path]] = {}
        for item in self.tmp_dir.iterdir():
            # Ignores subdirectories (like .trash) and hidden dotfiles
            if item.is_file() and not item.name.startswith("."):
                mtime = os.path.getmtime(item)
                dt_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
                grouped.setdefault(dt_str, []).append(item)

        return dict(sorted(grouped.items()))

    def generate_matrix_dict(self) -> dict:
        grouped = self.scan_by_date()
        today_str = get_current_datetime().strftime("%Y-%m-%d")
        ts = get_timestamp()

        total_files = sum(len(files) for files in grouped.values())
        total_bytes = sum(sum(f.stat().st_size for f in files) for files in grouped.values())

        dates_list = []
        for idx, (dt_str, files) in enumerate(grouped.items(), start=1):
            dt_bytes = sum(f.stat().st_size for f in files)
            file_items = []
            for f in sorted(files, key=lambda x: x.name):
                mtime_str = datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                file_items.append({
                    "filename": f.name,
                    "bytes": f.stat().st_size,
                    "modified_at": mtime_str
                })

            dates_list.append({
                "id": idx,
                "date": dt_str,
                "is_today": (dt_str == today_str),
                "file_count": len(files),
                "total_size_bytes": dt_bytes,
                "formatted_size": format_bytes(dt_bytes),
                "files": file_items
            })

        matrix = {
            "schema_version": "0.6.0",
            "timestamp": ts,
            "active_session_date": today_str,
            "total_files": total_files,
            "total_bytes": total_bytes,
            "formatted_total_size": format_bytes(total_bytes),
            "dates": dates_list,
            "actions_available": [
                {
                    "code": "a",
                    "label": "Apagar tudo EXCETO hoje",
                    "description": "Mover para quarentena (.trash) arquivos de sessões anteriores",
                    "is_default": True
                },
                {
                    "code": "d",
                    "label": "Selecionar datas específicas",
                    "description": "Mover para quarentena (.trash) apenas arquivos das datas indicadas",
                    "is_default": False
                },
                {
                    "code": "n",
                    "label": "Não apagar nada",
                    "description": "Preservar todos os arquivos temporários",
                    "is_default": False
                },
                {
                    "code": "t",
                    "label": "Apagar TUDO (inclusive hoje)",
                    "description": "Mover para quarentena (.trash) todos os arquivos temporários",
                    "is_default": False
                }
            ]
        }

        # Optional schema validation if file exists
        schema_file = Path(_scripts_root) / "schemas" / "tmp_cleanup_matrix.schema.json"
        if schema_file.exists() and jsonschema is not None:
            try:
                schema_data = json.loads(schema_file.read_text(encoding="utf-8"))
                jsonschema.validate(instance=matrix, schema=schema_data)
            except Exception as e:
                print(f"⚠️ [tmp_cleanup] Alerta de schema JSON: {e}", file=sys.stderr)

        return matrix

    def quarantine_files(self, files: List[Path]) -> int:
        trash = self.get_trash_dir()
        moved = 0
        for f in files:
            try:
                if f.exists() and f.is_file():
                    target = trash / f.name
                    if target.exists():
                        target.unlink()
                    shutil.move(str(f), str(target))
                    moved += 1
            except Exception as e:
                print(f"⚠️ Falha ao mover {f.name} para quarentena: {e}", file=sys.stderr)
        return moved

    def execute_action(self, code: str, dates_filter: Optional[List[str]] = None) -> Tuple[int, str]:
        grouped = self.scan_by_date()
        today_str = get_current_datetime().strftime("%Y-%m-%d")
        code = code.lower().strip()

        if code == "n":
            return 0, "Operação cancelada. Nenhum arquivo foi alterado."

        target_files: List[Path] = []
        if code == "a":
            target_files = [f for dt, files in grouped.items() if dt != today_str for f in files]
        elif code == "t":
            target_files = [f for files in grouped.values() for f in files]
        elif code == "d":
            if not dates_filter:
                return 0, "Nenhuma data ou ID especificado para a ação 'd'."
            date_keys = list(grouped.keys())
            for d in dates_filter:
                d_clean = d.strip()
                if d_clean.isdigit():
                    idx = int(d_clean)
                    if 1 <= idx <= len(date_keys):
                        target_files.extend(grouped[date_keys[idx - 1]])
                elif d_clean in grouped:
                    target_files.extend(grouped[d_clean])
        else:
            return 0, f"Código de ação '{code}' inválido."

        count = self.quarantine_files(target_files)
        msg = f"🧹 {count} arquivo(s) movidos para quarentena (~/.vitalia/tmp/.trash/)."
        return count, msg

    def display_matrix(self, grouped: Dict[str, List[Path]]) -> None:
        today_str = get_current_datetime().strftime("%Y-%m-%d")
        print("\n📊 Matriz de Arquivos Temporários (~/.vitalia/tmp/):")
        print("=" * 65)
        print(f"{'#':<3} | {'Data':<12} | {'Qtd Arquivos':<14} | {'Tamanho Total':<14} | {'Status'}")
        print("-" * 65)

        for idx, (dt_str, files) in enumerate(grouped.items(), start=1):
            total_bytes = sum(f.stat().st_size for f in files)
            is_today = (dt_str == today_str)
            status = "🟢 HOJE (Preservar)" if is_today else "🟡 Antigo"
            print(f"{idx:<3} | {dt_str:<12} | {len(files):<14} | {format_bytes(total_bytes):>14} | {status}")
        print("=" * 65)

    def run_interactive(self, auto_clean_old: bool = False) -> None:
        grouped = self.scan_by_date()
        if not grouped:
            print("✨ Pasta temporária já está limpa. Nenhum arquivo encontrado.")
            return

        if auto_clean_old:
            count, msg = self.execute_action("a")
            print(msg)
            return

        self.display_matrix(grouped)
        print("\nOpções de Limpeza:")
        print("  [a] (Recomendado) Apagar tudo EXCETO hoje")
        print("  [d] Selecionar datas específicas (ex: 1, 2)")
        print("  [n] (Padrão) Não apagar nada")
        print("  [t] Apagar TUDO (inclusive hoje)")

        if not sys.stdin.isatty():
            print("ℹ️ Executando em ambiente automatizado. Padrão: Não apagar nada.")
            return

        try:
            choice = input("\nEscolha uma opção [a/d/n/t] (Padrão: n): ").strip().lower() or "n"
            if choice == "d":
                sel = input("Digite os números das datas separados por vírgula (ex: 1, 2): ")
                dates_list = [x.strip() for x in sel.split(",") if x.strip()]
                count, msg = self.execute_action("d", dates_filter=dates_list)
                print(msg)
            else:
                count, msg = self.execute_action(choice)
                print(msg)
        except (KeyboardInterrupt, EOFError):
            print("\nOperação cancelada.")


def main():
    parser = argparse.ArgumentParser(
        description="Limpeza Interativa e Quarentena de Temporários — Vitalia Kit (v0.6.0)\n\n"
                    "Analisa a matriz de arquivos temporários por data em ~/.vitalia/tmp/,\n"
                    "emite o contrato JSON estruturado e executa ações de expurgo com quarentena em .trash/.",
        epilog="Exemplos de uso:\n"
               "  python3 tmp_cleanup.py --json-matrix\n"
               "  python3 tmp_cleanup.py --execute-action a\n"
               "  python3 tmp_cleanup.py --execute-action d --dates 2026-09-18\n"
               "  python3 tmp_cleanup.py --auto-clean-old\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--json-matrix", action="store_true", help="Emite a matriz temporária no formato JSON padronizado")
    parser.add_argument("--execute-action", choices=["a", "d", "n", "t"], help="Executa diretamente uma ação de expurgo (a: exceto hoje, d: datas especificas, n: nada, t: tudo)")
    parser.add_argument("--dates", nargs="+", help="Filtro de datas ou IDs para a ação 'd' (ex: 2026-09-18 ou 1 2)")
    parser.add_argument("--auto-clean-old", action="store_true", help="Equivalente a --execute-action a")

    args = parser.parse_args()

    cleaner = TmpCleanup()

    if args.json_matrix:
        matrix = cleaner.generate_matrix_dict()
        print(json.dumps(matrix, indent=2, ensure_ascii=False))
    elif args.execute_action:
        count, msg = cleaner.execute_action(args.execute_action, dates_filter=args.dates)
        print(msg)
    elif args.auto_clean_old:
        count, msg = cleaner.execute_action("a")
        print(msg)
    else:
        cleaner.run_interactive()


if __name__ == "__main__":
    main()
