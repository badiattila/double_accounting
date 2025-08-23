from abc import ABC, abstractmethod
from typing import Tuple

class Categorizer(ABC):
    @abstractmethod
    def predict(self, *, payee: str, narrative: str, amount: float) -> Tuple[str, float]:
        """Return (account_code, confidence)"""
