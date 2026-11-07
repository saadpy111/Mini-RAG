import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
from qdrant_client import models as qdrant_models
from qdrant_client.http.exceptions import UnexpectedResponse

from src.constants import ErrorCode
from src.helpers.result_pattern import ErrorType, Result
from src.vector_db.VectorDBEnums import DistanceMethodEnums
from src.vector_db.VectorDBModels import (
    VectorCollectionConfig,
    VectorRecord,
    VectorSearchFilter,
)
from src.vector_db.providers.QdrantDBProvider import QdrantDBProvider


def make_collection(
    name="chunks_lfm",
    dimension=1024,
    distance=DistanceMethodEnums.COSINE,
):
    return VectorCollectionConfig(
        name=name,
        dimension=dimension,
        distance=distance,
    )


def make_provider(collections=None, client=None):
    return QdrantDBProvider(
        client=client or AsyncMock(),
        collections=collections or [make_collection()],
    )


def collection_info(
    size=1024,
    distance=qdrant_models.Distance.COSINE,
    payload_schema=None,
):
    return SimpleNamespace(
        config=SimpleNamespace(
            params=SimpleNamespace(
                vectors=qdrant_models.VectorParams(
                    size=size,
                    distance=distance,
                )
            )
        ),
        payload_schema=payload_schema if payload_schema is not None else {},
    )


def test_initialize_reports_connection_success():
    client = AsyncMock()
    provider = make_provider(client=client)

    result = asyncio.run(provider.initialize())

    assert result.is_success is True
    client.get_collections.assert_awaited_once_with()


def test_initialize_translates_connection_failure():
    client = AsyncMock()
    client.get_collections.side_effect = RuntimeError("unreachable")
    provider = make_provider(client=client)

    result = asyncio.run(provider.initialize())

    assert result.is_success is False
    assert result.error.code == ErrorCode.VECTOR_DB_CONNECTION_FAILED
    assert result.error.type is ErrorType.SERVICE_UNAVAILABLE


def test_ensure_collections_creates_each_collection_with_own_dimension():
    client = AsyncMock()
    client.collection_exists.side_effect = [False, False]
    client.get_collection.side_effect = [
        collection_info(size=1024),
        collection_info(size=2048),
    ]
    provider = make_provider(
        collections=[
            make_collection(name="chunks_lfm", dimension=1024),
            make_collection(name="chunks_nemotron", dimension=2048),
        ],
        client=client,
    )

    result = asyncio.run(provider.ensure_collections())

    assert result.is_success is True
    assert client.create_collection.await_count == 2

    created = client.create_collection.await_args_list
    first_config = created[0].kwargs["vectors_config"]
    second_config = created[1].kwargs["vectors_config"]

    assert created[0].kwargs["collection_name"] == "chunks_lfm"
    assert first_config.size == 1024
    assert first_config.distance is qdrant_models.Distance.COSINE

    assert created[1].kwargs["collection_name"] == "chunks_nemotron"
    assert second_config.size == 2048
    assert second_config.distance is qdrant_models.Distance.COSINE

    assert client.create_payload_index.await_count == 2
    for call in client.create_payload_index.await_args_list:
        assert call.kwargs["field_name"] == "project_id"
        assert call.kwargs["field_schema"] is qdrant_models.PayloadSchemaType.KEYWORD
        assert call.kwargs["wait"] is True


def test_ensure_collections_reuses_matching_collection():
    client = AsyncMock()
    client.collection_exists.return_value = True
    client.get_collection.return_value = collection_info(size=1024)
    provider = make_provider(client=client)

    result = asyncio.run(provider.ensure_collections())

    assert result.is_success is True
    client.create_collection.assert_not_awaited()
    client.create_payload_index.assert_awaited_once()


def test_ensure_collections_skips_existing_project_payload_index():
    client = AsyncMock()
    client.collection_exists.return_value = True
    client.get_collection.return_value = collection_info(
        size=1024,
        payload_schema={"project_id": object()},
    )
    provider = make_provider(client=client)

    result = asyncio.run(provider.ensure_collections())

    assert result.is_success is True
    client.create_payload_index.assert_not_awaited()


def test_ensure_collections_rejects_dimension_mismatch():
    client = AsyncMock()
    client.collection_exists.return_value = True
    client.get_collection.return_value = collection_info(size=512)
    provider = make_provider(client=client)

    result = asyncio.run(provider.ensure_collections())

    assert result.is_success is False
    assert result.error.code == ErrorCode.VECTOR_DB_COLLECTION_MISMATCH
    assert "512" in result.error.message
    assert "1024" in result.error.message
    client.create_payload_index.assert_not_awaited()


def test_ensure_collections_rejects_distance_mismatch():
    client = AsyncMock()
    client.collection_exists.return_value = True
    client.get_collection.return_value = collection_info(
        size=1024,
        distance=qdrant_models.Distance.DOT,
    )
    provider = make_provider(client=client)

    result = asyncio.run(provider.ensure_collections())

    assert result.is_success is False
    assert result.error.code == ErrorCode.VECTOR_DB_COLLECTION_MISMATCH
    assert "dot" in result.error.message


def test_ensure_collections_rejects_named_vector_layout():
    client = AsyncMock()
    client.collection_exists.return_value = True
    client.get_collection.return_value = SimpleNamespace(
        config=SimpleNamespace(
            params=SimpleNamespace(
                vectors={
                    "default": qdrant_models.VectorParams(
                        size=1024,
                        distance=qdrant_models.Distance.COSINE,
                    )
                }
            )
        ),
        payload_schema={},
    )
    provider = make_provider(client=client)

    result = asyncio.run(provider.ensure_collections())

    assert result.is_success is False
    assert result.error.code == ErrorCode.VECTOR_DB_COLLECTION_MISMATCH


def test_ensure_collections_recovers_when_collection_already_exists():
    client = AsyncMock()
    client.collection_exists.return_value = False
    client.create_collection.side_effect = UnexpectedResponse(
        status_code=409,
        reason_phrase="Conflict",
        content=b"",
        headers=httpx.Headers(),
    )
    client.get_collection.return_value = collection_info(size=1024)
    provider = make_provider(client=client)

    result = asyncio.run(provider.ensure_collections())

    assert result.is_success is True
    client.get_collection.assert_awaited_once_with("chunks_lfm")
    client.create_payload_index.assert_awaited_once()


def test_ensure_collections_translates_creation_failure():
    client = AsyncMock()
    client.collection_exists.return_value = False
    client.create_collection.side_effect = RuntimeError("create failed")
    provider = make_provider(client=client)

    result = asyncio.run(provider.ensure_collections())

    assert result.is_success is False
    assert result.error.code == (
        ErrorCode.VECTOR_DB_COLLECTION_INITIALIZATION_FAILED
    )


def test_ensure_collections_translates_lookup_failure():
    client = AsyncMock()
    client.collection_exists.side_effect = RuntimeError("lookup failed")
    provider = make_provider(client=client)

    result = asyncio.run(provider.ensure_collections())

    assert result.is_success is False
    assert result.error.code == (
        ErrorCode.VECTOR_DB_COLLECTION_INITIALIZATION_FAILED
    )


def test_upsert_maps_record_to_qdrant_point():
    client = AsyncMock()
    provider = make_provider(client=client)
    vector_id = str(uuid4())
    vector = [0.25] * 1024
    record = VectorRecord(
        vector_id=vector_id,
        vector=vector,
        metadata={"project_id": 42, "chunk_id": "chunk-1"},
    )

    result = asyncio.run(provider.upsert("chunks_lfm", [record]))

    assert result.is_success is True
    assert result.value == 1
    client.upsert.assert_awaited_once()
    kwargs = client.upsert.await_args.kwargs
    assert kwargs["collection_name"] == "chunks_lfm"
    assert kwargs["wait"] is True

    point = kwargs["points"][0]
    assert str(point.id) == vector_id
    assert point.vector == vector
    assert point.payload == {
        "project_id": "42",
        "chunk_id": "chunk-1",
    }


def test_upsert_supports_per_collection_dimensions():
    client = AsyncMock()
    provider = make_provider(
        collections=[
            make_collection(name="chunks_lfm", dimension=1024),
            make_collection(name="chunks_nemotron", dimension=2048),
        ],
        client=client,
    )

    lfm_result = asyncio.run(
        provider.upsert(
            "chunks_lfm",
            [
                VectorRecord(
                    vector_id=str(uuid4()),
                    vector=[0.1] * 1024,
                    metadata={"project_id": "p1"},
                )
            ],
        )
    )
    nemotron_result = asyncio.run(
        provider.upsert(
            "chunks_nemotron",
            [
                VectorRecord(
                    vector_id=str(uuid4()),
                    vector=[0.2] * 2048,
                    metadata={"project_id": "p1"},
                )
            ],
        )
    )

    assert lfm_result.is_success is True
    assert nemotron_result.is_success is True
    assert client.upsert.await_count == 2


def test_upsert_rejects_dimension_for_selected_collection():
    client = AsyncMock()
    provider = make_provider(
        collections=[
            make_collection(name="chunks_lfm", dimension=1024),
            make_collection(name="chunks_nemotron", dimension=2048),
        ],
        client=client,
    )

    result = asyncio.run(
        provider.upsert(
            "chunks_nemotron",
            [
                VectorRecord(
                    vector_id=str(uuid4()),
                    vector=[0.1] * 1024,
                    metadata={"project_id": "p1"},
                )
            ],
        )
    )

    assert result.is_success is False
    assert result.error.code == ErrorCode.VECTOR_DB_INVALID_VECTOR_DIMENSION
    assert "1024" in result.error.message
    assert "2048" in result.error.message
    client.upsert.assert_not_awaited()


def test_upsert_rejects_invalid_uuid():
    client = AsyncMock()
    provider = make_provider(client=client)

    result = asyncio.run(
        provider.upsert(
            "chunks_lfm",
            [
                VectorRecord(
                    vector_id="not-a-uuid",
                    vector=[0.1] * 1024,
                    metadata={"project_id": "p1"},
                )
            ],
        )
    )

    assert result.is_success is False
    assert result.error.code == ErrorCode.VECTOR_DB_INVALID_VECTOR_ID
    client.upsert.assert_not_awaited()


def test_upsert_requires_project_id_payload():
    client = AsyncMock()
    provider = make_provider(client=client)

    result = asyncio.run(
        provider.upsert(
            "chunks_lfm",
            [
                VectorRecord(
                    vector_id=str(uuid4()),
                    vector=[0.1] * 1024,
                    metadata={"project_id": "   "},
                )
            ],
        )
    )

    assert result.is_success is False
    assert result.error.code == ErrorCode.VECTOR_DB_INVALID_PAYLOAD
    client.upsert.assert_not_awaited()


def test_upsert_with_empty_records_is_a_noop():
    client = AsyncMock()
    provider = make_provider(client=client)

    result = asyncio.run(provider.upsert("chunks_lfm", []))

    assert result.is_success is True
    assert result.value == 0
    client.upsert.assert_not_awaited()


def test_upsert_translates_qdrant_failure():
    client = AsyncMock()
    client.upsert.side_effect = RuntimeError("write failed")
    provider = make_provider(client=client)

    result = asyncio.run(
        provider.upsert(
            "chunks_lfm",
            [
                VectorRecord(
                    vector_id=str(uuid4()),
                    vector=[0.1] * 1024,
                    metadata={"project_id": "p1"},
                )
            ],
        )
    )

    assert result.is_success is False
    assert result.error.code == ErrorCode.VECTOR_DB_UPSERT_FAILED
    assert result.error.type is ErrorType.INTERNAL


def test_operations_reject_unconfigured_collection():
    provider = make_provider()

    result = asyncio.run(
        provider.upsert(
            "missing",
            [
                VectorRecord(
                    vector_id=str(uuid4()),
                    vector=[0.1] * 1024,
                    metadata={"project_id": "p1"},
                )
            ],
        )
    )

    assert result.is_success is False
    assert result.error.code == ErrorCode.VECTOR_DB_COLLECTION_NOT_CONFIGURED


def test_search_maps_results_and_project_filter():
    client = AsyncMock()
    vector_id = str(uuid4())
    client.query_points.return_value = SimpleNamespace(
        points=[
            SimpleNamespace(
                id=vector_id,
                score=0.87,
                payload={"project_id": "project-1"},
            ),
            SimpleNamespace(
                id=str(uuid4()),
                score=0.5,
                payload=None,
            ),
        ]
    )
    provider = make_provider(client=client)
    query_vector = [0.1] * 1024

    result = asyncio.run(
        provider.search(
            "chunks_lfm",
            query_vector,
            limit=5,
            filters=VectorSearchFilter(project_id="project-1"),
        )
    )

    assert result.is_success is True
    assert result.value[0].vector_id == vector_id
    assert result.value[0].score == 0.87
    assert result.value[0].metadata == {"project_id": "project-1"}
    assert result.value[1].metadata == {}

    kwargs = client.query_points.await_args.kwargs
    assert kwargs["collection_name"] == "chunks_lfm"
    assert kwargs["query"] == query_vector
    assert kwargs["limit"] == 5
    assert kwargs["with_payload"] is True
    assert kwargs["with_vectors"] is False

    query_filter = kwargs["query_filter"]
    condition = query_filter.must[0]
    assert condition.key == "project_id"
    assert condition.match.value == "project-1"


def test_search_without_filter_passes_none():
    client = AsyncMock()
    client.query_points.return_value = SimpleNamespace(points=[])
    provider = make_provider(client=client)

    result = asyncio.run(
        provider.search("chunks_lfm", [0.1] * 1024, limit=3)
    )

    assert result.is_success is True
    assert result.value == []
    assert client.query_points.await_args.kwargs["query_filter"] is None


def test_search_rejects_non_positive_limit():
    client = AsyncMock()
    provider = make_provider(client=client)

    result = asyncio.run(
        provider.search("chunks_lfm", [0.1] * 1024, limit=0)
    )

    assert result.is_success is False
    assert result.error.code == ErrorCode.VECTOR_DB_INVALID_SEARCH_LIMIT
    client.query_points.assert_not_awaited()


def test_search_rejects_wrong_query_dimension():
    client = AsyncMock()
    provider = make_provider(client=client)

    result = asyncio.run(
        provider.search("chunks_lfm", [0.1] * 2048, limit=3)
    )

    assert result.is_success is False
    assert result.error.code == ErrorCode.VECTOR_DB_INVALID_VECTOR_DIMENSION
    client.query_points.assert_not_awaited()


def test_search_rejects_blank_project_filter():
    client = AsyncMock()
    provider = make_provider(client=client)

    result = asyncio.run(
        provider.search(
            "chunks_lfm",
            [0.1] * 1024,
            limit=3,
            filters=VectorSearchFilter(project_id="   "),
        )
    )

    assert result.is_success is False
    assert result.error.code == ErrorCode.VECTOR_DB_INVALID_PROJECT_FILTER
    client.query_points.assert_not_awaited()


def test_search_translates_qdrant_failure():
    client = AsyncMock()
    client.query_points.side_effect = RuntimeError("search failed")
    provider = make_provider(client=client)

    result = asyncio.run(
        provider.search("chunks_lfm", [0.1] * 1024, limit=3)
    )

    assert result.is_success is False
    assert result.error.code == ErrorCode.VECTOR_DB_SEARCH_FAILED
    assert result.error.type is ErrorType.INTERNAL


def test_delete_by_ids_normalizes_identifiers():
    client = AsyncMock()
    provider = make_provider(client=client)
    vector_ids = [str(uuid4()), str(uuid4())]

    result = asyncio.run(
        provider.delete_by_ids("chunks_lfm", vector_ids)
    )

    assert result.is_success is True
    kwargs = client.delete.await_args.kwargs
    assert kwargs["collection_name"] == "chunks_lfm"
    assert kwargs["wait"] is True
    assert isinstance(kwargs["points_selector"], qdrant_models.PointIdsList)
    assert kwargs["points_selector"].points == vector_ids


def test_delete_by_ids_rejects_invalid_uuid():
    client = AsyncMock()
    provider = make_provider(client=client)

    result = asyncio.run(
        provider.delete_by_ids("chunks_lfm", ["not-a-uuid"])
    )

    assert result.is_success is False
    assert result.error.code == ErrorCode.VECTOR_DB_INVALID_VECTOR_ID
    client.delete.assert_not_awaited()


def test_delete_by_ids_with_empty_list_is_a_noop():
    client = AsyncMock()
    provider = make_provider(client=client)

    result = asyncio.run(provider.delete_by_ids("chunks_lfm", []))

    assert result.is_success is True
    client.delete.assert_not_awaited()


def test_delete_by_ids_translates_qdrant_failure():
    client = AsyncMock()
    client.delete.side_effect = RuntimeError("delete failed")
    provider = make_provider(client=client)

    result = asyncio.run(
        provider.delete_by_ids("chunks_lfm", [str(uuid4())])
    )

    assert result.is_success is False
    assert result.error.code == ErrorCode.VECTOR_DB_DELETE_FAILED


def test_delete_by_project_uses_payload_filter():
    client = AsyncMock()
    provider = make_provider(client=client)

    result = asyncio.run(
        provider.delete_by_project("chunks_lfm", "project-1")
    )

    assert result.is_success is True
    kwargs = client.delete.await_args.kwargs
    assert kwargs["collection_name"] == "chunks_lfm"
    assert kwargs["wait"] is True
    selector = kwargs["points_selector"]
    assert isinstance(selector, qdrant_models.FilterSelector)
    condition = selector.filter.must[0]
    assert condition.key == "project_id"
    assert condition.match.value == "project-1"


def test_delete_by_project_rejects_blank_project_id():
    client = AsyncMock()
    provider = make_provider(client=client)

    result = asyncio.run(provider.delete_by_project("chunks_lfm", "   "))

    assert result.is_success is False
    assert result.error.code == ErrorCode.VECTOR_DB_INVALID_PROJECT_FILTER
    client.delete.assert_not_awaited()


def test_delete_by_project_translates_qdrant_failure():
    client = AsyncMock()
    client.delete.side_effect = RuntimeError("delete failed")
    provider = make_provider(client=client)

    result = asyncio.run(provider.delete_by_project("chunks_lfm", "p1"))

    assert result.is_success is False
    assert result.error.code == ErrorCode.VECTOR_DB_DELETE_FAILED


def test_close_closes_shared_client():
    client = AsyncMock()
    provider = make_provider(client=client)

    asyncio.run(provider.close())

    client.close.assert_awaited_once_with()


def test_close_does_not_raise_on_failure():
    client = AsyncMock()
    client.close.side_effect = RuntimeError("close failed")
    provider = make_provider(client=client)

    asyncio.run(provider.close())

    client.close.assert_awaited_once_with()
