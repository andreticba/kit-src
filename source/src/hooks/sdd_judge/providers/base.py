# base.py | Vitalia SDD v0.6.0 | 16-09-2026 21:00(GMT-04:00)
from abc import ABC, abstractmethod
from typing import Optional


class LLMProvider(ABC):
    """Interface abstrata para provedores de LLM (Hardware-Agnostic P11)."""

    @abstractmethod
    def generate(self, prompt: str) -> Optional[str]:
        """Gera resposta a partir de um prompt text simples."""
        pass
