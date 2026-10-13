# __init__.py | Vitalia SDD v0.6.0 | 12-10-2026 21:10(GMT-04:00)
import os
import sys
from typing import Optional, Dict, Any
from sdd_judge.providers.base import LLMProvider, LLMResponse
from sdd_judge.providers.gemini import GeminiRESTProvider
from sdd_judge.providers.ollama import OllamaProvider

# FR-010 — Exit code semântico para falha de infraestrutura.
# EXIT_INFRA_FAIL = 2 distingue INFRA_FAIL de BLOCK constitucional (exit code 1).
EXIT_INFRA_FAIL = 2


class InfraFailError(RuntimeError):
    """Lançada quando Gemini API e Ollama falham simultaneamente (FR-010)."""
    pass


def get_provider(task_type: str = "reasoning") -> LLMProvider:
    """Fábrica de provedores respeitando variáveis de ambiente e fallback local (P11)."""
    # Se GEMINI_API_KEY ou GOOGLE_API_KEY estiver configurada, usa Gemini como primário
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return GeminiRESTProvider()
    return OllamaProvider(task_type=task_type)


def run_inference_with_failover(
    prompt: str,
    json_schema: Optional[Dict[str, Any]] = None,
    task_type: str = "reasoning"
) -> LLMResponse:
    """Tenta inferência primária via Gemini REST API; se falhar ou ausente, aciona Ollama local.

    Retorna LLMResponse com metadados de provedor, modelo e latência real (P15).
    Raises:
        InfraFailError: quando ambos os provedores falham (FR-010 / exit code 2).
    """
    # 1. Tentar Gemini se chave presente
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        gemini_provider = GeminiRESTProvider()
        model_name = gemini_provider._get_model()
        print(f"[SDDJudge] ⚡ Consultando Google Gemini API ({model_name} | temp=0.2)...", file=sys.stderr)
        res = gemini_provider.generate(prompt, json_schema=json_schema)
        if res is not None and res.content:
            return res
        print("[SDDJudge] ⚠️ Gemini API falhou ou sem resposta. Acionando fallback local (Ollama)...", file=sys.stderr)

    # 2. Provedor Local Ollama
    ollama_provider = OllamaProvider(task_type=task_type)
    print(f"[SDDJudge] 🦙 Consultando Ollama ({ollama_provider.model})...", file=sys.stderr)
    ollama_res = ollama_provider.generate(prompt, json_schema=json_schema)
    if ollama_res is not None and ollama_res.content:
        return ollama_res

    # 3. Ambos falharam — lançar InfraFailError para o cli.py converter em exit code 2
    raise InfraFailError(
        "Gemini API e Ollama indisponíveis. Nenhuma inferência possível. "
        "Verifique conectividade, cotas e se Ollama está rodando."
    )
