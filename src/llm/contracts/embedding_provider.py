"""Provider-agnostic text-embedding contract."""

from abc import ABC, abstractmethod

from src.helpers.result_pattern import Result


class EmbeddingProvider(ABC):
    """Contract for text-embedding integrations."""

    model_id: str

    @abstractmethod
    async def embed(self, text: str) -> Result[list[float]]:
        """Return the embedding vector for ``text``."""
