"""Async Qdrant implementation of the vector database contract."""

import logging
from collections.abc import Sequence
from uuid import UUID

from qdrant_client import AsyncQdrantClient
from qdrant_client import models as qdrant_models
from qdrant_client.http.exceptions import UnexpectedResponse

from src.helpers.result_pattern import Result, ResultError
from src.vector_db.VectorDBEnums import DistanceMethodEnums
from src.vector_db.VectorDBErrors import (
    collection_dimension_mismatch_error,
    collection_distance_mismatch_error,
    collection_initialization_error,
    collection_layout_unsupported_error,
    collection_not_configured_error,
    connection_failed_error,
    delete_failed_error,
    invalid_payload_error,
    invalid_project_filter_error,
    invalid_search_limit_error,
    invalid_vector_dimension_error,
    invalid_vector_id_error,
    project_vector_lookup_failed_error,
    search_failed_error,
    upsert_failed_error,
)
from src.vector_db.VectorDBInterface import VectorDBInterface
from src.vector_db.VectorDBModels import (
    VectorCollectionConfig,
    VectorRecord,
    VectorSearchFilter,
    VectorSearchResult,
)


logger = logging.getLogger(__name__)

DISTANCE_MAP = {
    DistanceMethodEnums.COSINE: qdrant_models.Distance.COSINE,
    DistanceMethodEnums.DOT: qdrant_models.Distance.DOT,
    DistanceMethodEnums.EUCLIDEAN: qdrant_models.Distance.EUCLID,
}

PROJECT_SCROLL_BATCH_SIZE = 256


class QdrantDBProvider(VectorDBInterface):
    """Qdrant provider bound to one shared async client.

    The provider owns no embedding logic. Callers choose a configured
    collection and pass vectors plus metadata through the shared contract.
    """

    def __init__(
        self,
        *,
        client: AsyncQdrantClient,
        collections: Sequence[VectorCollectionConfig],
    ) -> None:
        self._client = client
        self._collections = {
            collection.name: collection
            for collection in collections
        }

    async def initialize(self) -> Result[None]:
        try:
            await self._client.get_collections()
        except Exception:
            logger.exception("Failed to connect to Qdrant.")
            return Result.failure(connection_failed_error())

        return Result.success(None)

    async def ensure_collections(self) -> Result[None]:
        for config in self._collections.values():
            result = await self._ensure_collection(config)
            if not result.is_success:
                return result

        return Result.success(None)

    async def upsert(
        self,
        collection_name: str,
        records: Sequence[VectorRecord],
    ) -> Result[int]:
        config_result = self._get_collection_config(collection_name)
        if not config_result.is_success:
            return config_result

        config = config_result.value

        if not records:
            return Result.success(0)

        points: list[qdrant_models.PointStruct] = []

        for record in records:
            payload_result = self._build_payload(record)
            if not payload_result.is_success:
                return payload_result

            vector_id_result = self._normalize_vector_id(
                record.vector_id
            )
            if not vector_id_result.is_success:
                return vector_id_result

            actual_dimension = len(record.vector)
            if actual_dimension != config.dimension:
                return Result.failure(
                    invalid_vector_dimension_error(
                        collection_name=collection_name,
                        expected=config.dimension,
                        actual=actual_dimension,
                    )
                )

            points.append(
                qdrant_models.PointStruct(
                    id=vector_id_result.value,
                    vector=list(record.vector),
                    payload=payload_result.value,
                )
            )

        try:
            await self._client.upsert(
                collection_name=collection_name,
                points=points,
                wait=True,
            )
        except Exception:
            logger.exception(
                "Failed to upsert %s vector(s) into Qdrant collection '%s'.",
                len(points),
                collection_name,
            )
            return Result.failure(upsert_failed_error())

        return Result.success(len(points))

    async def search(
        self,
        collection_name: str,
        query_vector: Sequence[float],
        *,
        limit: int,
        filters: VectorSearchFilter | None = None,
    ) -> Result[list[VectorSearchResult]]:
        config_result = self._get_collection_config(collection_name)
        if not config_result.is_success:
            return config_result

        config = config_result.value

        if limit <= 0:
            return Result.failure(invalid_search_limit_error())

        actual_dimension = len(query_vector)
        if actual_dimension != config.dimension:
            return Result.failure(
                invalid_vector_dimension_error(
                    collection_name=collection_name,
                    expected=config.dimension,
                    actual=actual_dimension,
                )
            )

        query_filter_result = self._build_project_filter(filters)
        if not query_filter_result.is_success:
            return query_filter_result

        try:
            response = await self._client.query_points(
                collection_name=collection_name,
                query=list(query_vector),
                query_filter=query_filter_result.value,
                limit=limit,
                with_payload=True,
                with_vectors=False,
            )
        except Exception:
            logger.exception(
                "Failed to search Qdrant collection '%s'.",
                collection_name,
            )
            return Result.failure(search_failed_error())

        results = [
            VectorSearchResult(
                vector_id=str(point.id),
                score=float(point.score),
                metadata=dict(point.payload or {}),
            )
            for point in response.points
        ]

        return Result.success(results)

    async def delete_by_ids(
        self,
        collection_name: str,
        vector_ids: Sequence[str],
    ) -> Result[None]:
        config_result = self._get_collection_config(collection_name)
        if not config_result.is_success:
            return config_result

        if not vector_ids:
            return Result.success(None)

        normalized_ids: list[str] = []

        for vector_id in vector_ids:
            normalized_result = self._normalize_vector_id(vector_id)
            if not normalized_result.is_success:
                return normalized_result

            normalized_ids.append(normalized_result.value)

        try:
            await self._client.delete(
                collection_name=collection_name,
                points_selector=qdrant_models.PointIdsList(
                    points=normalized_ids,
                ),
                wait=True,
            )
        except Exception:
            logger.exception(
                "Failed to delete %s vector(s) from Qdrant collection '%s'.",
                len(normalized_ids),
                collection_name,
            )
            return Result.failure(delete_failed_error())

        return Result.success(None)

    async def list_ids_by_project(
        self,
        collection_name: str,
        project_id: str,
    ) -> Result[list[str]]:
        config_result = self._get_collection_config(collection_name)
        if not config_result.is_success:
            return config_result

        normalized_project_id = str(project_id).strip()
        if not normalized_project_id:
            return Result.failure(invalid_project_filter_error())

        vector_ids: list[str] = []
        offset = None

        try:
            while True:
                points, offset = await self._client.scroll(
                    collection_name=collection_name,
                    scroll_filter=self._project_filter(
                        normalized_project_id,
                    ),
                    limit=PROJECT_SCROLL_BATCH_SIZE,
                    offset=offset,
                    with_payload=False,
                    with_vectors=False,
                )

                vector_ids.extend(str(point.id) for point in points)

                if offset is None:
                    break
        except Exception:
            logger.exception(
                "Failed to list vectors for a project in Qdrant "
                "collection '%s'.",
                collection_name,
            )
            return Result.failure(project_vector_lookup_failed_error())

        return Result.success(vector_ids)

    async def delete_by_project(
        self,
        collection_name: str,
        project_id: str,
    ) -> Result[None]:
        config_result = self._get_collection_config(collection_name)
        if not config_result.is_success:
            return config_result

        normalized_project_id = str(project_id).strip()
        if not normalized_project_id:
            return Result.failure(invalid_project_filter_error())

        try:
            await self._client.delete(
                collection_name=collection_name,
                points_selector=qdrant_models.FilterSelector(
                    filter=self._project_filter(normalized_project_id),
                ),
                wait=True,
            )
        except Exception:
            logger.exception(
                "Failed to delete vectors for project in Qdrant "
                "collection '%s'.",
                collection_name,
            )
            return Result.failure(delete_failed_error())

        return Result.success(None)

    async def close(self) -> None:
        try:
            await self._client.close()
        except Exception:
            logger.exception("Failed to close the Qdrant client.")

    async def _ensure_collection(
        self,
        config: VectorCollectionConfig,
    ) -> Result[None]:
        try:
            exists = await self._client.collection_exists(config.name)

            if not exists:
                try:
                    await self._client.create_collection(
                        collection_name=config.name,
                        vectors_config=qdrant_models.VectorParams(
                            size=config.dimension,
                            distance=DISTANCE_MAP[config.distance],
                        ),
                    )
                except UnexpectedResponse as exc:
                    if exc.status_code != 409:
                        raise

                    # Another application instance created the collection
                    # concurrently. Validate the existing configuration.

            info = await self._client.get_collection(config.name)
            validation_error = self._validate_collection(config, info)
            if validation_error is not None:
                return Result.failure(validation_error)

            await self._ensure_project_payload_index(config.name, info)
        except Exception:
            logger.exception(
                "Failed to initialize Qdrant collection '%s'.",
                config.name,
            )
            return Result.failure(collection_initialization_error())

        return Result.success(None)

    def _validate_collection(
        self,
        config: VectorCollectionConfig,
        info: qdrant_models.CollectionInfo,
    ) -> ResultError | None:
        vectors_config = info.config.params.vectors

        if not isinstance(vectors_config, qdrant_models.VectorParams):
            return collection_layout_unsupported_error(config.name)

        if vectors_config.size != config.dimension:
            return collection_dimension_mismatch_error(
                collection_name=config.name,
                expected=config.dimension,
                actual=vectors_config.size,
            )

        expected_distance = DISTANCE_MAP[config.distance]
        if vectors_config.distance != expected_distance:
            return collection_distance_mismatch_error(
                collection_name=config.name,
                expected=config.distance.value,
                actual=vectors_config.distance.value.lower(),
            )

        return None

    async def _ensure_project_payload_index(
        self,
        collection_name: str,
        info: qdrant_models.CollectionInfo,
    ) -> None:
        if "project_id" in info.payload_schema:
            return

        await self._client.create_payload_index(
            collection_name=collection_name,
            field_name="project_id",
            field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
            wait=True,
        )

    def _get_collection_config(
        self,
        collection_name: str,
    ) -> Result[VectorCollectionConfig]:
        config = self._collections.get(collection_name)
        if config is None:
            return Result.failure(
                collection_not_configured_error(collection_name)
            )

        return Result.success(config)

    def _build_payload(
        self,
        record: VectorRecord,
    ) -> Result[dict]:
        payload = dict(record.metadata)
        project_id = payload.get("project_id")

        if project_id is None or not str(project_id).strip():
            return Result.failure(invalid_payload_error())

        payload["project_id"] = str(project_id)
        return Result.success(payload)

    def _normalize_vector_id(self, vector_id: str) -> Result[str]:
        try:
            return Result.success(str(UUID(str(vector_id))))
        except (TypeError, ValueError, AttributeError):
            return Result.failure(invalid_vector_id_error(str(vector_id)))

    def _build_project_filter(
        self,
        filters: VectorSearchFilter | None,
    ) -> Result[qdrant_models.Filter | None]:
        if filters is None or filters.project_id is None:
            return Result.success(None)

        normalized_project_id = str(filters.project_id).strip()
        if not normalized_project_id:
            return Result.failure(invalid_project_filter_error())

        return Result.success(
            self._project_filter(normalized_project_id)
        )

    def _project_filter(self, project_id: str) -> qdrant_models.Filter:
        return qdrant_models.Filter(
            must=[
                qdrant_models.FieldCondition(
                    key="project_id",
                    match=qdrant_models.MatchValue(value=project_id),
                )
            ]
        )
