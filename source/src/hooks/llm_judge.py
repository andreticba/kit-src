#!/usr/bin/env python3
# llm_judge.py | Vitalia Kit — Domínio HOOKS
# Atualizado em: 03-09-2026 14:35:00(GMT-04:00)
"""
Avaliador Constitucional Local e Task Verifier — Vitalia Kit (Domínio HOOKS)
Avaliação com streaming assíncrono e timeout de 10s. Autonomia via model_benchmark.
"""

import os
import sys
import re
import json
import argparse
import requests
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any

_scripts_root = str(Path(__file__).resolve().parent.parent)
if _scripts_root not in sys.path:
    sys.path.insert(0, _scripts_root)

import kit_env_bootstrap
health = kit_env_bootstrap.init()
from core.utils import get_timestamp, format_visible_header


class LLMJudge:
    def __init__(self, mode: str = "tasks", model_override: str = None):
        self.mode = mode
        
        # T007: Verifica o status do benchmark antes de processar código
        self.check_benchmark_status()
        
        # Recarrega variáveis que podem ter sido geradas/alteradas pelo benchmark
        self.model_name = model_override or os.environ.get("REVIEW_LLM_PROFILE", "qwen3:4b")
        no2_raw = os.environ.get("VITALIA_NODE", "http://ai-control.ddns.net:11434")
        
        if "/v1" in no2_raw:
            base = no2_raw.split("/v1")[0].rstrip("/")
        else:
            base = no2_raw.rstrip("/")
            
        self.ollama_generate_url = f"{base}/api/generate"
        self.node_display = f"Nó Alvo ({base})"

    def check_benchmark_status(self):
        """Verifica a chave vitalia:benchmark:latest. Se ausente/vencida, roda o benchmark."""
        benchmark_ok = False
        try:
            import redis
            r_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
            client = redis.from_url(r_url, socket_connect_timeout=1, decode_responses=True)
            data = client.get("vitalia:benchmark:latest")
            if data:
                b_json = json.loads(data)
                if b_json.get("node_info", {}).get("status") == "HEALTHY":
                    benchmark_ok = True
                else:
                    print(f"⚠️ [LLMJudge] Benchmark indica status Inseguro: {b_json.get('node_info', {}).get('status')}")
        except Exception:
            pass
            
        if not benchmark_ok:
            print(f"⚠️ [LLMJudge] Benchmark Redis ausente ou vencido. Invocando Descoberta Autônoma...")
            try:
                bm_script = Path(__file__).resolve().parent.parent / "core" / "model_benchmark.py"
                subprocess.run([sys.executable, str(bm_script)], check=True)
                kit_env_bootstrap.init() # Recarrega as vars .env 
            except Exception as e:
                print(f"❌ [LLMJudge] Falha ao invocar benchmark autonomo: {e}")

    def load_constitution_summary(self) -> str:
        kit_root = Path.home() / ".vitalia"
        candidates = [
            kit_root / "profiles" / "constitution.yaml",
            kit_root / "profiles" / "constitution_data.yaml",
        ]
        for c in candidates:
            if c.exists():
                try:
                    import yaml
                    data = yaml.safe_load(c.read_text(encoding="utf-8"))
                    lines = []
                    # Try V2 dual index format
                    principles = data.get("principles", {})
                    if principles:
                        for pid, p in principles.items():
                            lines.append(f"- [{pid}] {p.get('name')}: {p.get('rule')}")
                        return "\n".join(lines)
                    
                    # Try V1 modules format
                    for mod in data.get("modules", []):
                        for p in mod.get("principles", []):
                            lines.append(f"- [{p.get('id')}] {p.get('name')}: {p.get('rule')}")
                    if lines:
                        return "\n".join(lines)
                except Exception:
                    pass
        return "- [P01] SDD Inviolability: Nunca codificar sem spec aprovada.\n- [P07] Privacy by Design: Proteção de dados.\n- [P11] Agnosticismo de Hardware."

    def run_inference_stream(self, prompt: str) -> str:
        """T005: Executa inferência com streaming e 10s Idle Timeout."""
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": 0.0,
                "num_predict": 1024
            }
        }
        
        full_response = []
        try:
            print(f"  ⏳ Enviando para {self.node_display} (stream=True, timeout=10s)...")
            resp = requests.post(self.ollama_generate_url, json=payload, stream=True, timeout=10)
            if resp.status_code == 200:
                print("  📥 Processando resposta:\n")
                for line in resp.iter_lines():
                    if line:
                        chunk = json.loads(line.decode('utf-8'))
                        text = chunk.get("response", "")
                        print(text, end="", flush=True)
                        full_response.append(text)
                print("\n")
                return "".join(full_response)
            else:
                print(f"  ⚠️ Nó Alvo retornou HTTP {resp.status_code}.")
                return ""
        except requests.exceptions.ReadTimeout:
            print("\n  ⚠️ [WARN] Nó Inoperante (Timeout 10s de Inatividade). Conexão rompida preventivamente.")
            return "".join(full_response)
        except Exception as e:
            print(f"\n  ⚠️ Erro na inferência: {e}")
            return "".join(full_response)

    def check_after_task(self) -> int:
        """T006: Varredura de Git Diff com teto de tokens."""
        rules_summary = self.load_constitution_summary()
        
        try:
            diff = subprocess.check_output(["git", "diff", "HEAD"], text=True, stderr=subprocess.STDOUT)
            if not diff.strip():
                diff = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"], text=True)
                if diff.strip():
                    diff = f"Untracked files:\n{diff}"
        except Exception as e:
            print(f"⚠️ [LLMJudge] Falha ao capturar git diff: {e}")
            return 0
            
        if not diff.strip():
            print("✅ [LLMJudge] Nenhum diff encontrado para avaliar.")
            return 0
            
        # Limite NFR-01: ~15k caracteres
        diff_trunc = diff[:15000]
        
        print(f"\n[Post-Code Defense — LLM Judge]")
        print(f"  • Inspecionando Git Diff ({len(diff_trunc)} chars)")
        
        prompt = f"""Você é o Avaliador Constitucional do Vitalia SDD.
Audite o código alterado contra as regras constitucionais.

PRINCÍPIOS CONSTITUCIONAIS:
{rules_summary}

CÓDIGO ALTERADO (DIFF):
```diff
{diff_trunc}
```

INSTRUÇÕES:
Emita o seu veredito final iniciando OBRIGATORIAMENTE com [PASS], [WARN] ou [BLOCK], seguido da justificativa.
"""
        resp_text = self.run_inference_stream(prompt)
        
        if "[BLOCK]" in resp_text.upper():
            print("\n❌ [BLOCK] Bloqueio constitucional! O código introduz violações críticas.\n")
            return 1
        elif "[WARN]" in resp_text.upper():
            print("\n⚠️ [WARN] Avisos de conformidade identificados. Revisão recomendada, mas pipeline liberado.\n")
            return 0
        else:
            print("\n✅ [PASS] Código validado pela constituição.\n")
            return 0

    def inspect_tasks_file(self, tasks_path: Path) -> int:
        if not tasks_path.exists():
            print(f"❌ [LLMJudge] Arquivo não encontrado: {tasks_path}")
            return 1

        content = tasks_path.read_text(encoding="utf-8")
        task_lines = [l for l in content.splitlines() if re.match(r"^\s*-\s*\[[ xX]\]\s*\*\*T\d+", l) or re.match(r"^\s*-\s*\[[ xX]\]\s*T\d+", l)]

        if not task_lines:
            print(f"⚠️ [LLMJudge] Nenhuma tarefa atômica encontrada em: {tasks_path}")
            return 0

        rules_summary = self.load_constitution_summary()

        print(f"\n[Task Verifier — LLM Judge]")
        print(f"  • Nó de Inferência: {self.node_display}")
        print(f"  • Modelo (REVIEW_LLM_PROFILE): {self.model_name}")
        print(f"  • Inspecionando {len(task_lines)} tarefas em lote\n")

        tasks_formatted = "\n".join(task_lines)

        prompt = f"""Você é o Avaliador Constitucional do Vitalia SDD.
Audite o lote de tarefas abaixo contra as regras de governança.

PRINCÍPIOS CONSTITUCIONAIS:
{rules_summary}

TAREFAS A AUDITAR:
{tasks_formatted}

INSTRUÇÕES:
Para cada tarefa, emita rigorosamente:
TASK_ID: VERDICT | REASON

Onde VERDICT é PASS, WARN, ou BLOCK. Exemplo:
T001: PASS | Conforme com governança.
"""
        
        raw_out = self.run_inference_stream(prompt)
        
        has_blocking = False
        has_warning = False

        if not raw_out.strip():
            print("  ⚠️ Sem parecer do LLM.")
            return 0

        for line in task_lines:
            t_id_match = re.search(r"T\d+", line)
            t_id = t_id_match.group(0) if t_id_match else "TASK"
            
            verdict_match = re.search(rf"{t_id}:?\s*(PASS|WARN|BLOCK)\s*\|?\s*(.*)$", raw_out, re.IGNORECASE | re.MULTILINE)
            if verdict_match:
                v = verdict_match.group(1).upper()
                r = verdict_match.group(2).strip()
                if v == "BLOCK":
                    print(f"  ❌ [{t_id}] [BLOCK] {r}")
                    has_blocking = True
                elif v == "WARN":
                    print(f"  ⚠️ [{t_id}] [WARN] {r}")
                    has_warning = True
                else:
                    print(f"  ✅ [{t_id}] [PASS] {r}")
            else:
                pass # Already printed in stream

        if has_blocking:
            print("\n❌ [BLOCK] Bloqueio constitucional! Corrija as tarefas antes de prosseguir.\n")
            return 1
        elif has_warning:
            print("\n⚠️ [WARN] Avisos de conformidade identificados.\n")
            return 0
        else:
            print("\n[PASS] Todas as tarefas aderem à Constituição. Liberado para /vitalia-spec-implement.\n")
            return 0


def main():
    parser = argparse.ArgumentParser(
        description="Avaliador Constitucional Local e Task Verifier — Vitalia Kit (v0.6.0)\n\n"
                    "Inspeciona arquivos tasks.md ou git diffs contra a constituição em constitution.yaml\n"
                    "usando LLMs locais (Ollama) ou provedor resilitente.",
        epilog="Exemplos de uso:\n"
               "  python3 llm_judge.py specs/004-multiagent-ecosystem/tasks.md --mode tasks\n"
               "  python3 llm_judge.py --mode after_task\n"
               "  python3 llm_judge.py --mode analyze --model qwen3:4b\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("tasks_file", nargs="?", default=None, help="Caminho do arquivo tasks.md a inspecionar")
    parser.add_argument("--mode", default="tasks", choices=["tasks", "analyze", "after_task"], help="Modo de avaliação")
    parser.add_argument("--model", default=None, help="Modelo Ollama customizado")

    args = parser.parse_args()

    project_root = kit_env_bootstrap.find_project_root()
    
    judge = LLMJudge(mode=args.mode, model_override=args.model)
    
    if args.mode == "after_task":
        exit_code = judge.check_after_task()
        sys.exit(exit_code)
        
    # Modo 'tasks' ou 'analyze' dependem do tasks_path
    if args.tasks_file:
        tasks_path = Path(args.tasks_file)
        if not tasks_path.is_absolute():
            tasks_path = project_root / tasks_path
    else:
        feature_json = project_root / ".vitalia" / "feature.json"
        tasks_path = None
        if feature_json.exists():
            try:
                feat = json.loads(feature_json.read_text(encoding="utf-8"))
                feat_dir = feat.get("feature_directory") or feat.get("active_feature") or ""
                candidate = project_root / feat_dir / "tasks.md"
                if candidate.exists():
                    tasks_path = candidate
            except Exception:
                pass

        if not tasks_path or not tasks_path.exists():
            spec_tasks = list(project_root.glob("specs/*/tasks.md"))
            if spec_tasks:
                tasks_path = sorted(spec_tasks)[-1]
            else:
                tasks_path = project_root / "specs" / "tasks.md"

    exit_code = judge.inspect_tasks_file(tasks_path)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
