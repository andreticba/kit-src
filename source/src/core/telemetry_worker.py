import os
import sys
import json
import time
from pathlib import Path

# Adiciona o diretório src/ ao PYTHONPATH para o kit_env_bootstrap
import sys
from pathlib import Path
_scripts_root = str(Path(__file__).resolve().parent.parent)
if _scripts_root not in sys.path:
    sys.path.insert(0, _scripts_root)
import kit_env_bootstrap
kit_env_bootstrap.init()

try:
    import redis
except ImportError:
    redis = None

def find_events_file():
    """Busca ou cria o events.jsonl no repositorio alvo."""
    current = Path.cwd()
    while current != current.parent:
        if (current / ".vitalia").exists():
            mem_dir = current / ".vitalia" / "memory" / "data_storage"
            mem_dir.mkdir(parents=True, exist_ok=True)
            return mem_dir / "events.jsonl"
        current = current.parent
    
    # Fallback to local execution dir if not in a vitalia project
    fallback = Path.cwd() / ".vitalia" / "memory" / "data_storage"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback / "events.jsonl"

def main():
    if not redis:
        print("[ERRO] Módulo redis não instalado. O Telemetry Worker requer redis.")
        return

    r_url = os.environ.get("REDIS_URL") or "redis://localhost:6379/0"
    client = redis.from_url(r_url, decode_responses=True)
    
    events_file = find_events_file()
    print(f"[*] Telemetry Worker iniciado. Lendo de vitalia:telemetry_events")
    print(f"[*] Destino: {events_file}")
    
    # Inicia a leitura do ultimo ID (ou '0' para ler histórico pendente se quiser, mas '$' lê apenas os novos)
    last_id = '$'
    
    while True:
        try:
            # XREAD bloqueia por ate 5000ms esperando novos eventos
            streams = client.xread({"vitalia:telemetry_events": last_id}, count=10, block=5000)
            
            if streams:
                for stream_name, events in streams:
                    for event_id, event_data in events:
                        # Prepara o JSONLine
                        log_entry = {
                            "id": event_id,
                            "timestamp": time.time(),
                            "data": event_data
                        }
                        
                        # Append atomico (abrir e fechar no modo append)
                        with open(events_file, "a", encoding="utf-8") as f:
                            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                        
                        last_id = event_id
                        print(f"  [+] Evento salvo: {event_id} -> {event_data.get('event', 'unknown')}")
        except redis.exceptions.ConnectionError:
            print("[!] Conexão com Redis perdida. Tentando novamente em 5s...")
            time.sleep(5)
        except redis.exceptions.TimeoutError:
            # Expected on blocking reads (xread) when socket idle time exceeds python's internal threshold
            pass
        except KeyboardInterrupt:
            print("\n[*] Telemetry Worker encerrado pelo usuário.")
            break
        except Exception as e:
            print(f"[ERRO] Erro inesperado: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
