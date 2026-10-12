# __init__.py | Atualizado em: 21-09-2026 22:03:15(GMT-04:00)
# __init__.py | Vitalia SDD v0.6.0 | 21-09-2026 21:44(GMT-04:00)
import sys
from typing import Optional
from sdd_judge.providers.base import LLMProvider
from sdd_judge.providers.gemini import GeminiRESTProvider
from sdd_judge.providers.ollama import OllamaProvider

# FR-010 — Exit code semântico para falha de infraestrutura.
# EXIT_INFRA_FAIL = 2 distingue INFRA_FAIL de BLOCK constitucional (exit code 1).
EXIT_INFRA_FAIL = 2


class InfraFailError(RuntimeError):
    """Lançada quando Gemini API e Ollama falham simultaneamente.

    O cli.py captura esta excessão e encerra com sys.exit(EXIT_INFRA_FAIL=2),
    permitindo que callers (hook_runner, sdd_task_runner) distingam:
      exit 0 → PASS/WARN (constitucional)
      exit 1 → BLOCK  (constitucional)
      exit 2 → INFRA_FAIL (API indisponível)
    """
    pass


def run_inference_with_failover(prompt: str) -> Optional[str]:
    """Tenta inferência primária via Gemini REST API; se falhar ou ausente, aciona Ollama local.

    Raises:
        InfraFailError: quando ambos os providers falham. O caller deve encerrar com exit code 2.
    """
    gemini_provider = GeminiRESTProvider()
    model_name = gemini_provider._get_model()
    print(f"[SDDJudge] ⚡ Consultando Google Gemini API ({model_name} | temp=0.2)...", file=sys.stderr)
    res = gemini_provider.generate(prompt)
    if res is not None:
        return res

    print("[SDDJudge] ⚠️ Gemini API falhou ou indisponível. Acionando fallback local (Ollama)...", file=sys.stderr)
    ollama_provider = OllamaProvider()
    ollama_res = ollama_provider.generate(prompt)
    if ollama_res is not None:
        return ollama_res

    # Ambos falharam — lançar InfraFailError para o cli.py converter em exit code 2
    raise InfraFailError(
        "Gemini API e Ollama indisponíveis. Nenhuma inferência possível. "
        "Verifique conectividade, cotas e se Ollama está rodando."
    )
