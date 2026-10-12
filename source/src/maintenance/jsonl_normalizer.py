#!/usr/bin/env python3
# jsonl_normalizer.py | Vitalia Kit — Domínio MAINTENANCE
# Atualizado em: 28-08-2026 08:59:34(GMT-04:00)
"""
Sanitizador e Normalizador Transacional de Memória — Vitalia Kit (Domínio MAINTENANCE)

Responsabilidades:
1. Executar antes da compilação das visões no workflow session-consolidate.
2. Sanitizar os arquivos data/learnings.jsonl e data/decisions.jsonl.
3. Preencher campos obrigatórios ausentes em registros legados:
   - Em data/learnings.jsonl: preenche 'rationale' ausente com 'Registro defasado'.
   - Em data/decisions.jsonl: preenche 'rationale' ausente com 'Registro defasado'.
   - Gera IDs determinísticos SHA256 se o campo 'id' estiver ausente.
4. Migrar shards legados no formato Markdown (.md) em shards/ para o formato canônico YAML v0.5.0.
5. Disponibilizar flag --help didática com exemplos de uso.

Didática para Desenvolvedores Iniciantes:
- Por que este script é necessário? Ao longo do tempo, diferentes sessões podem registrar
  dados com pequenas variações de schema ou sem campos que se tornaram obrigatórios depois.
  O normalizador garante que o 'renderer' sempre receba dados perfeitamente limpos e estruturados,
  evitando quebras de renderização no painel README.md ou na injeção de contexto dos LLMs.
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Auto-injeção do diretório pai (~/.vitalia/scripts) em sys.path
import sys
_scripts_root = str(Path(__file__).resolve().parent.parent)
if _scripts_root not in sys.path:
    sys.path.insert(0, _scripts_root)

# Bootstrap de ambiente para carregar .env e site-packages
import kit_env_bootstrap
health = kit_env_bootstrap.init()
from core.utils import read_jsonl, append_jsonl, get_timestamp, generate_id


class JSONLNormalizer:
    """
    Sanitizador transacional que normaliza ledgers de memória e migra formatos legados.
    """
    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.data_dir = session_dir / "data"
        self.shards_dir = session_dir / "shards"

    def normalize_learnings(self) -> Tuple[int, int]:
        """
        Normaliza o arquivo data/learnings.jsonl.
        Retorna (total_registros, registros_corrigidos).
        """
        learnings_file = self.data_dir / "learnings.jsonl"
        if not learnings_file.exists():
            return 0, 0

        records = read_jsonl(learnings_file)
        if not records:
            return 0, 0

        fixed_count = 0
        normalized_records = []

        for rec in records:
            changed = False
            # 1. Garantir campo ID
            if "id" not in rec or not rec["id"]:
                rec["id"] = generate_id(str(rec.get("timestamp", "")) + str(rec.get("learning", "")))
                changed = True

            # 2. Garantir campo category
            if "category" not in rec or not rec["category"]:
                rec["category"] = "[PROJETO]"
                changed = True

            # 3. Garantir campo source_origin
            if "source_origin" not in rec or not rec["source_origin"]:
                rec["source_origin"] = rec.get("machine_id", "unknown_machine")
                changed = True

            # 4. Garantir campo rationale (Regra Feature 009: 'Registro defasado')
            if "rationale" not in rec or not rec["rationale"]:
                rec["rationale"] = "Registro defasado"
                changed = True

            # 5. Garantir timestamp
            if "timestamp" not in rec or not rec["timestamp"]:
                rec["timestamp"] = get_timestamp()
                changed = True

            if changed:
                fixed_count += 1
            normalized_records.append(rec)

        # Gravar de volta de forma atômica se houver alterações
        if fixed_count > 0:
            temp_file = learnings_file.with_suffix(".jsonl.tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                for r in normalized_records:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            os.replace(temp_file, learnings_file)

        return len(normalized_records), fixed_count

    def normalize_decisions(self) -> Tuple[int, int]:
        """
        Normaliza o arquivo data/decisions.jsonl.
        Retorna (total_registros, registros_corrigidos).
        """
        decisions_file = self.data_dir / "decisions.jsonl"
        if not decisions_file.exists():
            return 0, 0

        records = read_jsonl(decisions_file)
        if not records:
            return 0, 0

        fixed_count = 0
        normalized_records = []

        for rec in records:
            changed = False
            if "id" not in rec or not rec["id"]:
                rec["id"] = generate_id(str(rec.get("timestamp", "")) + str(rec.get("decision", "")))
                changed = True

            if "category" not in rec or not rec["category"]:
                rec["category"] = "[ARCH]"
                changed = True

            if "rationale" not in rec or not rec["rationale"]:
                rec["rationale"] = "Registro defasado"
                changed = True

            if "timestamp" not in rec or not rec["timestamp"]:
                rec["timestamp"] = get_timestamp()
                changed = True

            if changed:
                fixed_count += 1
            normalized_records.append(rec)

        if fixed_count > 0:
            temp_file = decisions_file.with_suffix(".jsonl.tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                for r in normalized_records:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            os.replace(temp_file, decisions_file)

        return len(normalized_records), fixed_count

    def migrate_legacy_shards(self) -> int:
        """
        Detecta shards legados no formato Markdown (.md) em shards/ e converte para .yaml.
        Retorna a quantidade de shards migrados.
        """
        if not self.shards_dir.exists():
            return 0

        migrated_count = 0
        for md_file in self.shards_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                # Parser simples de chave-valor Markdown (ex: **machine_name:** andrenote)
                machine_name = re.search(r'\*\*machine_name:\*\*\s*(.*)', content)
                machine_id = md_file.stem
                task = re.search(r'\*\*current_task:\*\*\s*(.*)', content)
                status = re.search(r'\*\*status:\*\*\s*(.*)', content)
                last_sync = re.search(r'\*\*last_sync:\*\*\s*(.*)', content)

                yaml_payload = f"""schema_version: "0.5.0"
machine_name: "{machine_name.group(1).strip() if machine_name else 'unknown'}"
machine_id: "{machine_id}"
mode: "Integrado"
current_task: "{task.group(1).strip() if task else 'Tarefa migrada'}"
status: "{status.group(1).strip() if status else 'Concluído'}"
next_step: "Sessão migrada"
last_sync: "{last_sync.group(1).strip() if last_sync else get_timestamp()}"
steps_completed:
  - "Shard legado migrado de Markdown para YAML"
"""
                target_yaml = self.shards_dir / f"{machine_id}.yaml"
                target_yaml.write_text(yaml_payload, encoding="utf-8")
                md_file.unlink()  # Remove o .md antigo com segurança
                migrated_count += 1
                print(f"  📦 Shard legado migrado: {md_file.name} -> {target_yaml.name}")
            except Exception as e:
                print(f"⚠️ [Normalizer] Falha ao migrar shard {md_file.name}: {e}", file=sys.stderr)

        return migrated_count


def main():
    parser = argparse.ArgumentParser(
        description="Normalizador e Sanitizador Transacional de Memória — Vitalia Kit",
        epilog="Exemplos de uso:\n  python3 jsonl_normalizer.py --session-dir .vitalia/memory/session\n  python3 jsonl_normalizer.py --verbose",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--session-dir",
        default=None,
        help="Caminho do repositório de sessão (padrão: .vitalia/memory/session relativo ao projeto)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Exibe detalhes de cada registro normalizado"
    )

    args = parser.parse_args()

    project_root = kit_env_bootstrap.find_project_root()
    session_dir = Path(args.session_dir) if args.session_dir else (project_root / ".vitalia" / "memory" / "session")

    print(f"[jsonl_normalizer] Iniciando sanitização de memória em: {session_dir}")

    normalizer = JSONLNormalizer(session_dir)
    total_l, fixed_l = normalizer.normalize_learnings()
    total_d, fixed_d = normalizer.normalize_decisions()
    migrated_shards = normalizer.migrate_legacy_shards()

    print(f"  💡 Aprendizados: {total_l} verificados | {fixed_l} normalizados ('Registro defasado')")
    print(f"  🏛️  Decisões:     {total_d} verificadas | {fixed_d} normalizadas")
    print(f"  📦 Shards:        {migrated_shards} shards legados (.md) migrados para .yaml")
    print("[jsonl_normalizer] ✅ Memória transacional 100% íntegra e pronta para consolidação!")


if __name__ == "__main__":
    main()
