# ollama.py | Vitalia SDD v0.6.0 | 16-09-2026 21:00(GMT-04:00)
import os
import sys
from typing import Optional
from sdd_judge.providers.base import LLMProvider

try:
    import requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False


class OllamaProvider(LLMProvider):
    """Provedor Ollama local para fallback de inferência."""

    def __init__(self, model: Optional[str] = None, url: Optional[str] = None):
        self.model = model or os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b").strip()
        self.url = url or os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate").strip()

    def generate(self, prompt: str) -> Optional[str]:
        if not _REQUESTS_OK:
            print("[OllamaProvider] ⚠️ Pacote 'requests' não instalado.", file=sys.stderr)
            return None

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }

        try:
            resp = requests.post(self.url, json=payload, timeout=480)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response", "")
            else:
                print(f"[OllamaProvider] ⚠️ HTTP {resp.status_code}: {resp.text[:150]}", file=sys.stderr)
                return None
        except Exception as e:
            print(f"[OllamaProvider] ⚠️ Erro de conexão com Ollama: {e}", file=sys.stderr)
            return None
