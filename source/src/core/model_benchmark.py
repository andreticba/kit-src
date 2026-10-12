import os
import sys
import json
import time
import datetime
import urllib.request
import urllib.error
import urllib.parse
import argparse
from pathlib import Path

# Adiciona o diretorio pai ao PYTHONPATH para importar hardware_discovery e redis
import sys
from pathlib import Path
_scripts_root = str(Path(__file__).resolve().parent.parent)
if _scripts_root not in sys.path:
    sys.path.insert(0, _scripts_root)
import kit_env_bootstrap
kit_env_bootstrap.init()

from core.hardware_discovery import get_nodes_from_env, ping_node, get_ram_usage, get_vram_usage

try:
    import redis
    r_url = os.environ.get("REDIS_URL")
    redis_client = redis.from_url(r_url, decode_responses=True)
except ImportError:
    redis_client = None
    print("[WARN] Módulo redis não instalado. O benchmark não será gravado no barramento.")

def get_models_from_node(url):
    """Bate no endpoint /api/tags para listar modelos do nó."""
    # Garante que a URL não termine com barra e aponte para /api/tags
    base_url = url.rstrip('/')
    tags_url = f"{base_url}/api/tags"
    
    try:
        req = urllib.request.Request(tags_url)
        with urllib.request.urlopen(req, timeout=3.0) as response:
            data = json.loads(response.read().decode('utf-8'))
            return [model['name'] for model in data.get('models', [])]
    except (urllib.error.URLError, json.JSONDecodeError, socket.timeout):
        return []

def run_inference(url, model_name, prompt):
    """Executa uma inferência com stream=True para evitar timeout de request gigante."""
    api_url = f"{url.rstrip('/')}/api/generate"
    payload = json.dumps({
        "model": model_name,
        "prompt": prompt,
        "stream": True
    }).encode('utf-8')
    
    req = urllib.request.Request(api_url, data=payload, headers={'Content-Type': 'application/json'})
    
    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=10.0) as response:
            final_metrics = {}
            for line in response:
                if line:
                    chunk = json.loads(line.decode('utf-8'))
                    if chunk.get("done"):
                        final_metrics = chunk
                        break
                        
        duration_ms = (time.time() - start_time) * 1000
        
        # O Ollama retorna eval_count e eval_duration em nanosegundos
        eval_count = final_metrics.get('eval_count', 0)
        eval_duration_ns = final_metrics.get('eval_duration', 0)
        
        if eval_duration_ns > 0:
            tps = eval_count / (eval_duration_ns / 1_000_000_000.0)
        else:
            tps = 0.0
            
        return {
            "duration_ms": round(duration_ms, 2),
            "tokens_per_second": round(tps, 2),
            "eval_count": eval_count
        }
    except Exception as e:
        print(f"[ERRO] Falha na inferência: {e}")
        return {"duration_ms": 0, "tokens_per_second": 0.0, "eval_count": 0}

def update_env_file(chosen_node_url, chosen_model):
    """Atualiza as variaveis REVIEW_LLM_PROFILE e VITALIA_NODE no arquivo .env."""
    from core.hardware_discovery import find_env_file
    env_path = find_env_file()
    if not env_path:
        print("[WARN] Arquivo .env não encontrado. Seleção não foi persistida.")
        return
        
    lines = []
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    new_lines = []
    found_profile = False
    found_node = False
    
    for line in lines:
        if line.startswith('REVIEW_LLM_PROFILE='):
            new_lines.append(f"REVIEW_LLM_PROFILE={chosen_model}\n")
            found_profile = True
        elif line.startswith('VITALIA_NODE='):
            new_lines.append(f"VITALIA_NODE={chosen_node_url}\n")
            found_node = True
        else:
            new_lines.append(line)
            
    if not found_profile:
        new_lines.append(f"REVIEW_LLM_PROFILE={chosen_model}\n")
    if not found_node:
        new_lines.append(f"VITALIA_NODE={chosen_node_url}\n")
        
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("[OK] Arquivo .env atualizado com as seleções.")

def main():
    parser = argparse.ArgumentParser(
        description="Benchmark e Calibração Autônoma de Modelos — Vitalia Kit (v0.6.0)\n\n"
                    "Executa testes de latência (Cold Run + 3 Warm Runs) nos nós Ollama,\n"
                    "calcula TPS (tokens por segundo) e atualiza o .env com a melhor seleção.",
        epilog="Exemplos de uso:\n"
               "  python3 model_benchmark.py\n"
               "  python3 model_benchmark.py --auto-select 1\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--auto-select", type=int, default=None, help="Seleciona automaticamente o índice da opção (1-based) sem pedir input HITL")

    args = parser.parse_args()

    print("=== Vitalia SDD: Model Benchmark & Hardware Discovery ===")
    nodes = get_nodes_from_env()
    
    available_options = []
    option_idx = 1
    
    print("\n[Buscando Nós e Modelos...]")
    for node in nodes:
        url = node['url']
        is_up = ping_node(url)
        if is_up:
            models = get_models_from_node(url)
            for model in models:
                available_options.append({"node": node, "model": model})
                print(f"[{option_idx}] Nó: {node['name']} ({url}) | Modelo: {model}")
                option_idx += 1
        else:
            print(f"[-] Nó {node['name']} ({url}) está OFFLINE.")
            
    if not available_options:
        print("\n[ERRO] Nenhum nó respondendo ou sem modelos instalados. Abortando.")
        sys.exit(1)
        
    print("\n--- Descoberta de Hardware (Local) ---")
    ram_info = get_ram_usage()
    if ram_info:
        print(f"RAM: {ram_info['available_gb']} GB Livres / {ram_info['total_gb']} GB Total ({ram_info['percent']}% Uso)")
        
    vram_info = get_vram_usage()
    if vram_info:
        for idx, gpu in enumerate(vram_info):
            print(f"GPU {idx}: {gpu['free_gb']} GB VRAM Livres / {gpu['total_gb']} GB Total")
    else:
        print("GPU: Nenhuma placa NVIDIA suportada encontrada (nvidia-smi).")

    # Matriz Interativa (HITL)
    if args.auto_select is not None:
        idx = args.auto_select - 1
    elif not sys.stdin.isatty():
        print("ℹ️ Ambiente automatizado detectado. Selecionando a primeira combinação disponível.")
        idx = 0
    else:
        try:
            choice = input("\nSelecione o número da combinação (Nó/Modelo) para o Benchmark (ou Ctrl+C para abortar): ")
            idx = int(choice.strip()) - 1
            if idx < 0 or idx >= len(available_options):
                print("Seleção inválida.")
                sys.exit(1)
        except (ValueError, KeyboardInterrupt, EOFError):
            print("\nBenchmark cancelado pelo usuário.")
            sys.exit(0)
        
    selected = available_options[idx]
    target_url = selected['node']['url']
    target_model = selected['model']
    
    print(f"\n[Iniciando Benchmark em {target_url} com {target_model}]")
    
    # 1 Cold Run
    print(">> Executando Cold Run...")
    cold_metrics = run_inference(target_url, target_model, "O que é engenharia de software? Seja muito breve.")
    print(f"   Cold Run: {cold_metrics['duration_ms']} ms | {cold_metrics['tokens_per_second']} TPS")
    
    # 3 Warm Runs
    warm_runs = []
    print(">> Executando Warm Runs...")
    for i in range(1, 4):
        prompt = f"Descreva brevemente o conceito de Agnosticismo de Hardware. Geração {i}."
        metrics = run_inference(target_url, target_model, prompt)
        metrics['run_id'] = i
        warm_runs.append(metrics)
        print(f"   Warm Run {i}: {metrics['duration_ms']} ms | {metrics['tokens_per_second']} TPS")
        
    avg_tps = sum(m['tokens_per_second'] for m in warm_runs) / len(warm_runs) if warm_runs else 0
    print(f"\n[Resultado Final] TPS Médio (Warm): {avg_tps:.2f} tokens/s")
    
    # Determina Status (HEALTHY vs OOM_RISK)
    status = "HEALTHY"
    if avg_tps < 5.0:
        status = "OOM_RISK"
        print("[!] ATENÇÃO: TPS abaixo de 5.0. Risco de OOM (Out Of Memory) ou Throttling térmico.")
        
    # Grava no Redis respeitando o schema
    payload = {
        "timestamp": datetime.datetime.now().strftime("%d-%m-%Y %H:%M(GMT-04:00)"),
        "node_info": {
            "url": target_url,
            "status": status,
            "ping_ms": 0 # Pode ser calculado depois se necessário
        },
        "hardware_state": {
            "ram_total_gb": ram_info['total_gb'] if ram_info else 0,
            "ram_available_gb": ram_info['available_gb'] if ram_info else 0,
            "vram_total_gb": vram_info[0]['total_gb'] if vram_info else 0,
            "vram_used_gb": vram_info[0]['used_gb'] if vram_info else 0
        },
        "model_tested": target_model,
        "inference_metrics": {
            "cold_start": cold_metrics,
            "warm_runs": warm_runs,
            "avg_tokens_per_second": round(avg_tps, 2)
        },
        "ttl_seconds": 3600 # 1 Hora de validade do Benchmark
    }
    
    if redis_client:
        redis_client.set("vitalia:benchmark:latest", json.dumps(payload), ex=3600)
        print("[OK] Benchmark persistido no Redis (vitalia:benchmark:latest) com TTL de 1 hora.")
        
    # Atualiza .env
    update_env_file(target_url, target_model)
    
if __name__ == "__main__":
    main()
