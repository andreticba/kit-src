# ollama.py | Vitalia SDD v0.6.0 | 12-10-2026 21:10(GMT-04:00)
import os
import sys
import time
from typing import Optional, Dict, Any
from sdd_judge.providers.base import LLMProvider, LLMResponse

try:
    import requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False


class OllamaProvider(LLMProvider):
    """Provedor Ollama local com suporte a JSON Schema, matriz dual de modelos (P11) e telemetria (P15)."""

    def __init__(self, model: Optional[str] = None, url: Optional[str] = None, task_type: str = "reasoning"):
        self.url = url or os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate").strip()
        self.task_type = task_type
        
        if model:
            self.model = model.strip()
        elif task_type == "coding":
            self.model = os.environ.get("OLLAMA_CODER_MODEL", os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")).strip()
        else:
            self.model = os.environ.get("OLLAMA_REASONING_MODEL", os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")).strip()

        # Configuração de timeouts com leitura de .env
        try:
            self.connect_timeout = float(os.environ.get("OLLAMA_CONNECT_TIMEOUT", "10").strip())
        except ValueError:
            self.connect_timeout = 10.0

        try:
            self.read_timeout = float(os.environ.get("OLLAMA_TIMEOUT", "30").strip())
        except ValueError:
            self.read_timeout = 30.0

    def generate(self, prompt: str, json_schema: Optional[Dict[str, Any]] = None) -> Optional[LLMResponse]:
        if not _REQUESTS_OK:
            print("[OllamaProvider] ⚠️ Pacote 'requests' não instalado.", file=sys.stderr)
            return None

        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }

        if json_schema:
            payload["format"] = json_schema

        t_start = time.perf_counter()
        try:
            resp = requests.post(
                self.url,
                json=payload,
                timeout=(self.connect_timeout, self.read_timeout)
            )
            elapsed = time.perf_counter() - t_start

            if resp.status_code == 200:
                data = resp.json()
                content = data.get("response", "")
                return LLMResponse(
                    content=content,
                    provider="Ollama",
                    model=self.model,
                    latency=elapsed,
                    status_code=200,
                    raw_data=data
                )
            else:
                print(f"[OllamaProvider] ⚠️ HTTP {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
                return LLMResponse(
                    content="",
                    provider="Ollama",
                    model=self.model,
                    latency=elapsed,
                    status_code=resp.status_code
                )
        except requests.exceptions.ConnectTimeout:
            elapsed = time.perf_counter() - t_start
            print(f"[OllamaProvider] ⚠️ Timeout de conexão ({self.connect_timeout}s) com {self.url}", file=sys.stderr)
            return None
        except requests.exceptions.ReadTimeout:
            elapsed = time.perf_counter() - t_start
            print(f"[OllamaProvider] ⚠️ Timeout de leitura ({self.read_timeout}s) aguardando inferência de {self.model}", file=sys.stderr)
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"[OllamaProvider] ⚠️ Erro de conexão com Ollama: {e}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"[OllamaProvider] ⚠️ Erro inesperado na requisição Ollama: {e}", file=sys.stderr)
            return None
