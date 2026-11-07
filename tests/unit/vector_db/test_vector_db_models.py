import pytest
from pydantic import ValidationError

from src.vector_db.VectorDBEnums import DistanceMethodEnums
from src.vector_db.VectorDBModels import (
    VectorCollectionConfig,
    VectorRecord,
    VectorSearchFilter,
    VectorSearchResult,
)


def test_collection_config_uses_cosine_by_default():
    config = VectorCollectionConfig(
        name="document_chunks_lfm_350m",
        dimension=1024,
    )

    assert config.distance is DistanceMethodEnums.COSINE


def test_collection_config_accepts_explicit_distance():
    config = VectorCollectionConfig(
        name="document_chunks_nemotron_1b",
        dimension=2048,
        distance="euclidean",
    )

    assert config.dimension == 2048
    assert config.distance is DistanceMethodEnums.EUCLIDEAN


def test_collection_config_rejects_empty_name():
    with pytest.raises(ValidationError):
        VectorCollectionConfig(name="   ", dimension=1024)


def test_collection_config_rejects_non_positive_dimension():
    with pytest.raises(ValidationError):
        VectorCollectionConfig(name="chunks", dimension=0)


def test_vector_record_metadata_defaults_are_independent():
    first = VectorRecord(vector_id="id-1", vector=(0.1, 0.2))
    second = VectorRecord(vector_id="id-2", vector=(0.3, 0.4))

    assert first.metadata == {}
    assert second.metadata == {}
    assert first.metadata is not second.metadata


def test_vector_search_result_metadata_defaults_are_independent():
    first = VectorSearchResult(vector_id="id-1", score=0.9)
    second = VectorSearchResult(vector_id="id-2", score=0.8)

    assert first.metadata == {}
    assert second.metadata == {}
    assert first.metadata is not second.metadata


def test_vector_search_filter_defaults_to_no_project():
    assert VectorSearchFilter().project_id is None
