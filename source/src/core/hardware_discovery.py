import os
import socket
import subprocess
import re
from pathlib import Path

def find_env_file():
    """Busca o arquivo .env a partir do diretório atual subindo até a raiz."""
    current = Path.cwd()
    while current != current.parent:
        env_path = current / ".env"
        if env_path.exists():
            return env_path
        current = current.parent
    return None

def get_nodes_from_env():
    """Lê todos os nós declarados no .env (variáveis terminadas em _IP ou _URL)."""
    env_path = find_env_file()
    nodes = []
    
    if not env_path:
        # Tenta ler as variaveis de ambiente caso ja tenham sido carregadas
        for k, v in os.environ.items():
            if ("NODE_" in k and ("_IP" in k or "_URL" in k)) or "OLLAMA_HOST" in k:
                nodes.append({"name": k, "url": v})
        
        # Se não achou nada, devolve fallback de localhost
        if not nodes:
             nodes.append({"name": "DEFAULT_NODE", "url": "http://localhost:11434"})
        return nodes

    # Parse manual sem depender de dotenv
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip().strip("'").strip('"')
                if ("NODE_" in key and ("_IP" in key or "_URL" in key)) or key == "OLLAMA_HOST":
                    # Formatar URL se for só IP
                    if not val.startswith("http"):
                        val = f"http://{val}"
                    if not re.search(r':\d+$', val):
                        val = f"{val}:11434"
                    nodes.append({"name": key, "url": val})
    
    if not nodes:
        nodes.append({"name": "DEFAULT_NODE", "url": "http://localhost:11434"})
    
    return nodes

def ping_node(url, timeout=2.0):
    """Verifica se o nó está respondendo na porta."""
    # Parse URL to get host and port
    # ex: http://192.168.1.5:11434
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        host = parsed.hostname or url
        port = parsed.port or 11434
        
        start_time = os.times().elapsed if hasattr(os.times(), 'elapsed') else 0
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except (socket.timeout, socket.error, ConnectionRefusedError):
        return False

def get_vram_usage():
    """Obtém dados da VRAM usando nvidia-smi sem depender de pynvml."""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.total,memory.used,memory.free', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, check=True
        )
        # Output ex: 6144, 1024, 5120
        lines = result.stdout.strip().split('\n')
        gpus = []
        for line in lines:
            parts = [int(p.strip()) for p in line.split(',')]
            if len(parts) == 3:
                total, used, free = parts
                gpus.append({
                    "total_gb": round(total / 1024, 2),
                    "used_gb": round(used / 1024, 2),
                    "free_gb": round(free / 1024, 2)
                })
        return gpus
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def get_ram_usage():
    """Obtém uso de RAM usando psutil ou arquivo nativo linux."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "percent": mem.percent
        }
    except ImportError:
        # Fallback to /proc/meminfo for Linux
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = {}
                for line in f:
                    parts = line.split(':')
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = int(parts[1].strip().split()[0]) # kb
                        meminfo[key] = val
            total = meminfo.get('MemTotal', 0) * 1024
            available = meminfo.get('MemAvailable', meminfo.get('MemFree', 0)) * 1024
            return {
                "total_gb": round(total / (1024**3), 2),
                "available_gb": round(available / (1024**3), 2),
                "percent": round(100 - (available / total * 100), 1) if total > 0 else 0
            }
        except FileNotFoundError:
            return None

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Descoberta e Sondagem de Hardware e Nós — Vitalia Kit (v0.6.0)\n\n"
                    "Inspeciona uso de RAM, VRAM (nvidia-smi) e conectividade com nós de inferência Ollama.",
        epilog="Exemplos de uso:\n"
               "  python3 hardware_discovery.py\n"
               "  python3 hardware_discovery.py --help\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    args = parser.parse_args()

    print("--- Hardware Discovery Test ---")
    nodes = get_nodes_from_env()
    print(f"Nodes encontrados: {nodes}")
    for node in nodes:
        is_up = ping_node(node['url'])
        print(f"[{node['name']}] {node['url']} -> {'ONLINE' if is_up else 'OFFLINE'}")
    
    print("\n--- RAM ---")
    print(get_ram_usage())
    
    print("\n--- VRAM (nvidia-smi) ---")
    print(get_vram_usage())
