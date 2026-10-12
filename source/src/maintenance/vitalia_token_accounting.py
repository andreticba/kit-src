#!/usr/bin/env python3
# vitalia_token_accounting.py | Atualizado em: 21-09-2026 22:03:15(GMT-04:00)
# vitalia_token_accounting.py | Vitalia SDD v0.6.0 | 21-09-2026 21:55(GMT-04:00)
"""
Contabilidade de Cotas de API — Vitalia Kit v0.6.0

Lê os logs de telemetria diária (gemini_transactions_YYYYMMDD.jsonl) e exibe
o consumo de requisições por modelo (Flash vs. PRO) comparado às cotas gratuitas,
com alertas visuais quando o consumo se aproxima dos limites.

Cotas gratuitas padrão (Google AI Studio — verificado em 21-09-2026):
  gemini-3.6-flash  → 1.500 RPD (requests per day)
  gemini-3.1-pro    → 50 RPD

Exemplos:
  # Consumo de hoje:
  python3 vitalia_token_accounting.py --today

  # Consumo de uma data específica:
  python3 vitalia_token_accounting.py --date 20260921

  # Saída em JSON estruturado (para parsing externo):
  python3 vitalia_token_accounting.py --today --json

Exit codes:
  0  — sucesso (incluindo quando arquivo não existe → consumo zero)
  1  — erro de leitura/parse do arquivo de telemetria
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

# ── Fuso horário do projeto (GMT-4) ─────────────────────────────────────────
VITALIA_TIMEZONE = timezone(timedelta(hours=-4))

# ── Cotas gratuitas por modelo (RPD = requests per day) ─────────────────────
# Fonte: https://ai.google.dev/gemini-api/docs/rate-limits (verificado 21-09-2026)
MODEL_QUOTAS: Dict[str, int] = {
    "gemini-3.6-flash":        1_500,
    "gemini-3.6-flash-latest": 1_500,
    "gemini-3.1-pro-preview":  50,
    "gemini-3.1-pro":          50,
    "gemini-pro":              50,
    "gemini-flash":            1_500,
}
DEFAULT_FLASH_QUOTA = 1_500
DEFAULT_PRO_QUOTA   = 50

# Thresholds de alerta
WARN_THRESHOLD     = 0.80   # ⚠️  > 80%
CRITICAL_THRESHOLD = 0.95   # 🚨  > 95%


def resolve_kit_dir() -> Path:
    """Resolve o diretório do Kit Global (~/.vitalia/ ou override via env)."""
    return Path(os.environ.get("VITALIA_KIT_DIR", Path.home() / ".vitalia")).expanduser()


def get_transactions_path(kit_dir: Path, date_str: str) -> Path:
    """Retorna o caminho do arquivo de telemetria para a data informada."""
    return kit_dir / "tmp" / f"gemini_transactions_{date_str}.jsonl"


def load_transactions(file_path: Path) -> List[dict]:
    """Lê e parseia o arquivo JSONL de transações. Retorna lista de dicts."""
    if not file_path.exists():
        return []
    transactions = []
    with open(file_path, encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                transactions.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"⚠️  Linha {i} inválida ignorada: {e}", file=sys.stderr)
    return transactions


def aggregate_by_model(transactions: List[dict]) -> Dict[str, int]:
    """Agrega o número de requisições por nome de modelo."""
    counts: Dict[str, int] = {}
    for tx in transactions:
        model = tx.get("model", tx.get("model_name", "unknown")).strip()
        counts[model] = counts.get(model, 0) + 1
    return counts


def get_quota(model: str) -> Tuple[int, str]:
    """Retorna (cota_rpd, categoria) para um modelo. Categoria: 'flash', 'pro' ou 'unknown'."""
    model_lower = model.lower()
    for known_model, quota in MODEL_QUOTAS.items():
        if known_model in model_lower:
            category = "flash" if "flash" in model_lower else "pro"
            return quota, category

    # Heurística por nome
    if "flash" in model_lower:
        return DEFAULT_FLASH_QUOTA, "flash"
    if "pro" in model_lower or "preview" in model_lower:
        return DEFAULT_PRO_QUOTA, "pro"
    return DEFAULT_FLASH_QUOTA, "unknown"


def status_icon(pct: float) -> str:
    """Retorna ícone de status baseado no percentual de uso da cota."""
    if pct >= CRITICAL_THRESHOLD:
        return "🚨"
    if pct >= WARN_THRESHOLD:
        return "⚠️ "
    return "✅"


def format_table(counts: Dict[str, int], date_str: str) -> str:
    """Formata tabela ASCII com consumo por modelo."""
    if not counts:
        return f"📭 Nenhuma transação registrada em {date_str}.\n   Arquivo: gemini_transactions_{date_str}.jsonl"

    lines = [
        f"\n📊 Consumo de API — {date_str}",
        "─" * 72,
        f"{'Modelo':<35} {'Req. Hoje':>10} {'Cota/dia':>10} {'% Uso':>8}  Status",
        "─" * 72,
    ]

    totals_flash = totals_pro = 0
    quota_flash = quota_pro = 0

    for model, count in sorted(counts.items()):
        quota, category = get_quota(model)
        pct = count / quota if quota > 0 else 0.0
        icon = status_icon(pct)
        lines.append(f"{model:<35} {count:>10,} {quota:>10,} {pct*100:>7.1f}%  {icon}")

        if category == "flash":
            totals_flash += count
            quota_flash = max(quota_flash, quota)
        elif category in ("pro", "unknown"):
            totals_pro += count
            quota_pro = max(quota_pro, quota)

    lines.append("─" * 72)

    # Totais por categoria
    if quota_flash > 0:
        pct_f = totals_flash / quota_flash
        lines.append(f"{'TOTAL Flash':<35} {totals_flash:>10,} {quota_flash:>10,} {pct_f*100:>7.1f}%  {status_icon(pct_f)}")
    if quota_pro > 0:
        pct_p = totals_pro / quota_pro
        lines.append(f"{'TOTAL Pro':<35} {totals_pro:>10,} {quota_pro:>10,} {pct_p*100:>7.1f}%  {status_icon(pct_p)}")

    lines.append("─" * 72)
    lines.append(f"\nLimites: Flash={DEFAULT_FLASH_QUOTA:,} RPD | Pro={DEFAULT_PRO_QUOTA} RPD (Google AI Studio free tier)")
    lines.append("Fonte: https://ai.google.dev/gemini-api/docs/rate-limits")
    return "\n".join(lines)


def format_json(counts: Dict[str, int], date_str: str) -> str:
    """Formata saída JSON estruturada."""
    models = []
    for model, count in sorted(counts.items()):
        quota, category = get_quota(model)
        pct = count / quota if quota > 0 else 0.0
        models.append({
            "model": model,
            "requests_today": count,
            "quota_rpd": quota,
            "usage_pct": round(pct * 100, 2),
            "status": "CRITICAL" if pct >= CRITICAL_THRESHOLD else ("WARN" if pct >= WARN_THRESHOLD else "OK"),
            "category": category,
        })
    return json.dumps({
        "date": date_str,
        "models": models,
        "thresholds": {"warn": WARN_THRESHOLD, "critical": CRITICAL_THRESHOLD},
    }, indent=2, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="vitalia_token_accounting.py",
        description="Contabilidade de Cotas de API Gemini — Vitalia Kit v0.6.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Consumo de hoje (fuso GMT-4):
  python3 vitalia_token_accounting.py --today

  # Consumo de uma data específica:
  python3 vitalia_token_accounting.py --date 20260921

  # Saída em JSON estruturado:
  python3 vitalia_token_accounting.py --today --json

Exit codes:
  0  — sucesso
  1  — erro de leitura do arquivo de telemetria
"""
    )

    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument(
        "--today", action="store_true",
        help="Usar a data atual (fuso GMT-4 do projeto)"
    )
    date_group.add_argument(
        "--date", metavar="YYYYMMDD",
        help="Data específica no formato YYYYMMDD (ex: 20260921)"
    )
    parser.add_argument(
        "--json", action="store_true", dest="output_json",
        help="Emitir saída em JSON estruturado em vez de tabela ASCII"
    )

    args = parser.parse_args()

    # Resolver data
    if args.today:
        date_str = datetime.now(VITALIA_TIMEZONE).strftime("%Y%m%d")
    else:
        date_str = args.date
        if not (len(date_str) == 8 and date_str.isdigit()):
            print(f"❌ Formato de data inválido: '{date_str}'. Use YYYYMMDD.", file=sys.stderr)
            return 1

    kit_dir = resolve_kit_dir()
    tx_path = get_transactions_path(kit_dir, date_str)

    try:
        transactions = load_transactions(tx_path)
    except OSError as e:
        print(f"❌ Erro ao ler arquivo de telemetria: {e}", file=sys.stderr)
        return 1

    counts = aggregate_by_model(transactions)

    if args.output_json:
        print(format_json(counts, date_str))
    else:
        if not transactions:
            print(f"📭 Nenhuma transação em {date_str}.")
            print(f"   Arquivo esperado: {tx_path}")
        else:
            print(format_table(counts, date_str))

    return 0


if __name__ == "__main__":
    sys.exit(main())
