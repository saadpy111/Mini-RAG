"""Shared, provider-independent vector database models."""

from dataclasses import dataclass, field
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field

from src.vector_db.VectorDBEnums import DistanceMethodEnums


class VectorCollectionConfig(BaseModel):
    """Configuration for one isolated vector collection.

    A collection is tied to a single vector space. Callers must use a
    different collection for embeddings produced by different models.
    """

    model_config = ConfigDict(
        frozen=True,
        str_strip_whitespace=True,
    )

    name: str = Field(..., min_length=1)
    dimension: int = Field(..., gt=0)
    distance: DistanceMethodEnums = DistanceMethodEnums.COSINE


@dataclass(frozen=True, slots=True)
class VectorRecord:
    """A vector to insert or update.

    ``vector_id`` remains a plain string in the shared contract. Providers
    that require a specific identifier format validate it internally.
    """

    vector_id: str
    vector: Sequence[float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VectorSearchResult:
    """One provider-independent vector search result."""

    vector_id: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VectorSearchFilter:
    """Application-level filters supported by vector search."""

    project_id: str | None = None
