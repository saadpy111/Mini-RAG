"""Provider-independent vector database interfaces."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from src.helpers.result_pattern import Result
from src.vector_db.VectorDBModels import (
    VectorRecord,
    VectorSearchFilter,
    VectorSearchResult,
)


class VectorStore(ABC):
    """Vector operations used by application services.

    Business logic depends on this narrow interface so it cannot initialize
    providers, manage collections, or close shared clients.
    """

    @abstractmethod
    async def upsert(
        self,
        collection_name: str,
        records: Sequence[VectorRecord],
    ) -> Result[int]:
        """Insert or update vectors in the named collection."""

    @abstractmethod
    async def search(
        self,
        collection_name: str,
        query_vector: Sequence[float],
        *,
        limit: int,
        filters: VectorSearchFilter | None = None,
    ) -> Result[list[VectorSearchResult]]:
        """Return the most similar vectors in the named collection."""

    @abstractmethod
    async def delete_by_ids(
        self,
        collection_name: str,
        vector_ids: Sequence[str],
    ) -> Result[None]:
        """Delete vectors by their application-level identifiers."""

    @abstractmethod
    async def delete_by_project(
        self,
        collection_name: str,
        project_id: str,
    ) -> Result[None]:
        """Delete all vectors belonging to a project in the collection."""


class VectorDBInterface(VectorStore, ABC):
    """Full provider contract used by lifecycle and administration code."""

    @abstractmethod
    async def initialize(self) -> Result[None]:
        """Validate provider connectivity."""

    @abstractmethod
    async def ensure_collections(self) -> Result[None]:
        """Create or validate every configured vector collection."""

    @abstractmethod
    async def close(self) -> None:
        """Release provider resources."""
