# gemini.py | Atualizado em: 21-09-2026 22:03:15(GMT-04:00)
# gemini.py | Vitalia SDD v0.6.0 | 18-09-2026 15:42(GMT-04:00)
import os
import sys
import time
import json
import random
import re
import socket
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
from sdd_judge.providers.base import LLMProvider

try:
    import requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

# Fuso horário padrão imutável do ecossistema Vitalia (UTC-4 / America/Cuiaba - P04)
VITALIA_TIMEZONE = timezone(timedelta(hours=-4))


class GeminiRESTProvider(LLMProvider):
    """Provedor Gemini REST API com resiliência avançada (P11), Full Jitter, parsing de retryDelay e Telemetria Transacional (P07)."""

    def __init__(
        self,
        max_retries: Optional[int] = None,
        base_delay: Optional[float] = None,
        max_delay: Optional[float] = None,
        telemetry_file: Optional[str] = None
    ):
        self._bootstrap_env()
        
        self.max_retries = max_retries if max_retries is not None else int(os.environ.get("GEMINI_MAX_RETRIES", "5"))
        self.base_delay = base_delay if base_delay is not None else float(os.environ.get("GEMINI_BASE_RETRY_DELAY", "3.0"))
        self.max_delay = max_delay if max_delay is not None else float(os.environ.get("GEMINI_MAX_RETRY_DELAY", "60.0"))
        self.telemetry_file = telemetry_file

    def _bootstrap_env(self) -> None:
        """Carrega o ambiente utilizando o kit_env_bootstrap padrão do kit."""
        try:
            _src_dir = str(Path(__file__).resolve().parent.parent.parent.parent)
            if _src_dir not in sys.path:
                sys.path.insert(0, _src_dir)
            import kit_env_bootstrap
            kit_env_bootstrap.init()
        except Exception as e:
            print(f"[GeminiRESTProvider] ⚠️ Falha ao executar kit_env_bootstrap: {e}", file=sys.stderr)

    def _get_api_key(self) -> Optional[str]:
        """Obtém a chave da API Gemini do ambiente com bootstrap de fallback."""
        for var in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
            val = os.environ.get(var, "").strip()
            if val:
                return val

        self._bootstrap_env()

        for var in ["GEMINI_API_KEY", "GOOGLE_API_KEY"]:
            val = os.environ.get(var, "").strip()
            if val:
                return val
        return None

    def _get_model(self) -> str:
        """Obtém o modelo configurado via .env (P11) com fallback para gemini-3.6-flash.

        Prioridade de resolução (FR-001 — Roteamento Híbrido):
        1. GEMINI_MODEL — injetado pelo hook_runner via env_copia (roteamento por fase SDD)
        2. GEMINI_MODEL_FLASH — fallback quando não há roteamento ativo
        """
        self._bootstrap_env()
        # FR-001: respeitar GEMINI_MODEL injetado pelo hook_runner (roteamento PRO/FLASH por fase)
        model = os.environ.get("GEMINI_MODEL", "").strip()
        if not model:
            model = os.environ.get("GEMINI_MODEL_FLASH", "gemini-3.6-flash").strip()
        return model

    def _get_telemetry_file_path(self) -> Path:
        """Resolve o caminho canônico do arquivo de telemetria diária em ~/.vitalia/tmp/."""
        if self.telemetry_file:
            return Path(self.telemetry_file)

        kit_dir = Path(os.environ.get("VITALIA_KIT_DIR", Path.home() / ".vitalia")).expanduser()
        date_str = datetime.now(VITALIA_TIMEZONE).strftime("%Y%m%d")
        return kit_dir / "tmp" / f"gemini_transactions_{date_str}.jsonl"

    def _parse_retry_delay(self, response_data: Dict[str, Any]) -> Optional[float]:
        """T003: Extrai o tempo de retry sugerido no erro HTTP 429/503 da API do Google (RetryInfo / QuotaFailure)."""
        if not response_data or not isinstance(response_data, dict):
            return None

        try:
            error_details = response_data.get("error", {}).get("details", [])
            if isinstance(error_details, list):
                for detail in error_details:
                    if isinstance(detail, dict) and detail.get("@type", "").endswith("RetryInfo"):
                        retry_delay_str = detail.get("retryDelay", "")
                        match = re.match(r"^([0-9]+(?:\.[0-9]+)?)s$", str(retry_delay_str))
                        if match:
                            return float(match.group(1))
        except Exception:
            pass
        return None

    def _calculate_backoff(self, attempt: int, response_data: Optional[Dict[str, Any]] = None) -> float:
        """T004: Calcula o tempo de espera utilizando retryDelay oficial se disponível ou Full Jitter."""
        if response_data:
            suggested_delay = self._parse_retry_delay(response_data)
            if suggested_delay is not None:
                return min(suggested_delay, self.max_delay)

        # Full Jitter: Sleep = random(0, min(max_delay, base_delay * 2^(attempt-1)))
        max_backoff = min(self.max_delay, self.base_delay * (2 ** (attempt - 1)))
        return random.uniform(0.0, max_backoff)

    def _log_telemetry(self, model: str, status_code: int, elapsed_ms: float, usage_metadata: Optional[Dict[str, Any]] = None) -> None:
        """T005: Registra telemetria sanitizada de consumo de tokens e desempenho em arquivo append-only (P07 & P04)."""
        try:
            telemetry_path = self._get_telemetry_file_path()
            telemetry_path.parent.mkdir(parents=True, exist_ok=True)

            now_str = datetime.now(VITALIA_TIMEZONE).strftime("%d-%m-%Y %H:%M:%S(GMT-04:00)")
            machine_name = os.environ.get("VITALIA_MACHINE_NAME") or socket.gethostname()
            machine_id = hashlib.sha256(machine_name.encode("utf-8")).hexdigest()[:8]

            record = {
                "schema_version": "0.6.0",
                "schema_type": "gemini_telemetry",
                "timestamp": now_str,
                "machine_id": machine_id,
                "machine_name": machine_name,
                "pid": os.getpid(),
                "model": model,
                "status_code": status_code,
                "elapsed_ms": round(elapsed_ms, 2),
                "tokens": {
                    "prompt": usage_metadata.get("promptTokenCount", 0) if usage_metadata else 0,
                    "candidates": usage_metadata.get("candidatesTokenCount", 0) if usage_metadata else 0,
                    "thoughts": usage_metadata.get("thoughtsTokenCount", 0) if usage_metadata else 0,
                    "total": usage_metadata.get("totalTokenCount", 0) if usage_metadata else 0
                } if usage_metadata else {},
                "service_tier": usage_metadata.get("serviceTier", "standard") if usage_metadata else "standard"
            }
            with open(telemetry_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            # P12: Resiliência de I/O de observabilidade
            print(f"⚠️ [GeminiRESTProvider] Falha ao gravar telemetria: {e}", file=sys.stderr)

    def generate(self, prompt: str) -> Optional[str]:
        """T010: Loop principal de geração com resiliência, Full Jitter, Fail-Fast e Telemetria P07."""
        if not _REQUESTS_OK:
            print("[GeminiRESTProvider] ⚠️ Pacote 'requests' não instalado.", file=sys.stderr)
            return None

        api_key = self._get_api_key()
        if not api_key:
            print("[GeminiRESTProvider] ⚠️ Nenhuma chave GEMINI_API_KEY ou GOOGLE_API_KEY configurada.", file=sys.stderr)
            return None

        model = self._get_model()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2}
        }
        headers = {"Content-Type": "application/json"}

        for attempt in range(1, self.max_retries + 1):
            t_start = time.time()
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=90)
                elapsed_ms = (time.time() - t_start) * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    usage_metadata = data.get("usageMetadata")
                    self._log_telemetry(model, 200, elapsed_ms, usage_metadata)
                    
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                    return ""

                elif resp.status_code in (429, 503):
                    error_json = None
                    try:
                        error_json = resp.json()
                    except Exception:
                        pass
                    
                    backoff = self._calculate_backoff(attempt, error_json)
                    print(
                        f"⚠️ [GeminiRESTProvider] HTTP {resp.status_code} ({'Rate Limit' if resp.status_code == 429 else 'Indisponível'}). "
                        f"Aguardando {backoff:.1f}s (Tentativa {attempt}/{self.max_retries})...",
                        file=sys.stderr
                    )
                    time.sleep(backoff)

                else:
                    # Fail Fast para erros não-recuperáveis (400, 401, 403, 404)
                    print(f"⚠️ [GeminiRESTProvider] HTTP {resp.status_code} (Erro Não-Recuperável): {resp.text[:200]}", file=sys.stderr)
                    return None

            except Exception as e:
                elapsed_ms = (time.time() - t_start) * 1000
                backoff = self._calculate_backoff(attempt)
                print(f"⚠️ [GeminiRESTProvider] Erro de rede ({e}). Aguardando {backoff:.1f}s...", file=sys.stderr)
                time.sleep(backoff)

        return None
