# base.py | Vitalia SDD v0.6.0 | 12-10-2026 21:10(GMT-04:00)
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class LLMResponse:
    """Encapsula o resultado da inferência com telemetria e metadados transparentes (P15)."""
    content: str
    provider: str
    model: str
    latency: float
    status_code: int = 200
    raw_data: Optional[Dict[str, Any]] = field(default=None)

    def __str__(self) -> str:
        return self.content


class LLMProvider(ABC):
    """Interface abstrata para provedores de LLM (Hardware-Agnostic P11)."""

    @abstractmethod
    def generate(self, prompt: str, json_schema: Optional[Dict[str, Any]] = None) -> Optional[LLMResponse]:
        """Gera resposta a partir de um prompt text simples ou com gramática estruturada JSON Schema."""
        pass
