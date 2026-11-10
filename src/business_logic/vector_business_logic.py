"""Application use cases for vector indexing and semantic search."""

import logging
from uuid import NAMESPACE_URL, uuid5

from bson import ObjectId
from pymongo.errors import PyMongoError

from src.constants import ErrorCode, ErrorMessage
from src.helpers.result_pattern import ErrorType, Result, ResultError
from src.llm.contracts import EmbeddingProvider
from src.llm.factories import EmbeddingProviderFactory
from src.models.data_chunk import DataChunk
from src.models.project import Project
from src.repositories.data_chunk_repository import DataChunkRepository
from src.repositories.project_repository import ProjectRepository
from src.vector_db.VectorDBInterface import VectorStore
from src.vector_db.VectorDBModels import (
    VectorRecord,
    VectorSearchFilter,
    VectorSearchResult,
)


logger = logging.getLogger(__name__)


def chunk_vector_id(chunk_id: ObjectId) -> str:
    """Return a deterministic UUID accepted by vector providers."""

    return str(uuid5(NAMESPACE_URL, f"mini-rag:chunk:{chunk_id}"))


class VectorBusinessLogic:
    def __init__(
        self,
        chunk_repository: DataChunkRepository,
        project_repository: ProjectRepository,
        embedding_factory: EmbeddingProviderFactory,
        vector_store: VectorStore,
        collection_name: str,
    ):
        self.chunk_repository = chunk_repository
        self.project_repository = project_repository
        self.embedding_factory = embedding_factory
        self.vector_store = vector_store
        self.collection_name = collection_name

    async def index_project(
        self,
        project_id: str,
        do_reset: bool = False,
    ) -> Result[int]:
        project_result = await self._resolve_project(project_id)

        if not project_result.is_success:
            return project_result

        project = project_result.value

        try:
            chunks = await self.chunk_repository.get_all_by_project_id(
                project.id
            )
        except PyMongoError:
            return Result.failure(
                ResultError(
                    code=ErrorCode.CHUNK_LOOKUP_FAILED,
                    message=ErrorMessage.CHUNK_LOOKUP_FAILED,
                    type=ErrorType.INTERNAL,
                )
            )

        if not chunks:
            return Result.failure(
                ResultError(
                    code=ErrorCode.NO_CHUNKS_TO_INDEX,
                    message=ErrorMessage.NO_CHUNKS_TO_INDEX,
                    type=ErrorType.UNPROCESSABLE,
                )
            )

        provider_result = self.embedding_factory.create()

        if not provider_result.is_success:
            return Result.failure(provider_result.error)

        records_result = await self._build_vector_records(
            chunks=chunks,
            provider=provider_result.value,
            project_id=project.project_id,
        )

        if not records_result.is_success:
            return Result.failure(records_result.error)

        records = records_result.value

        # The new vector set is complete at this point. Existing IDs are
        # listed before upserting so stale ones can be identified, but nothing
        # is deleted until the new vectors have been stored successfully.
        existing_ids: set[str] = set()

        if do_reset:
            existing_ids_result = (
                await self.vector_store.list_ids_by_project(
                    self.collection_name,
                    project.project_id,
                )
            )

            if not existing_ids_result.is_success:
                return Result.failure(existing_ids_result.error)

            existing_ids = set(existing_ids_result.value)

        upsert_result = await self.vector_store.upsert(
            self.collection_name,
            records,
        )

        if not upsert_result.is_success:
            return Result.failure(upsert_result.error)

        indexed_count = upsert_result.value or 0

        if do_reset:
            new_ids = {record.vector_id for record in records}
            stale_ids = sorted(existing_ids - new_ids)

            if stale_ids:
                delete_result = await self.vector_store.delete_by_ids(
                    self.collection_name,
                    stale_ids,
                )

                if not delete_result.is_success:
                    logger.error(
                        "New vectors were stored for project '%s', but "
                        "stale vectors could not be removed.",
                        project.project_id,
                    )
                    return Result.failure(delete_result.error)

        return Result.success(indexed_count)

    async def search_project(
        self,
        project_id: str,
        query: str,
        limit: int = 5,
    ) -> Result[list[VectorSearchResult]]:
        normalized_query = query.strip()

        if not normalized_query:
            return Result.failure(
                ResultError(
                    code=ErrorCode.EMPTY_SEARCH_QUERY,
                    message=ErrorMessage.EMPTY_SEARCH_QUERY,
                    type=ErrorType.VALIDATION,
                )
            )

        if limit <= 0:
            return Result.failure(
                ResultError(
                    code=ErrorCode.VECTOR_DB_INVALID_SEARCH_LIMIT,
                    message=ErrorMessage.VECTOR_DB_INVALID_SEARCH_LIMIT,
                    type=ErrorType.VALIDATION,
                )
            )

        project_result = await self._resolve_project(project_id)

        if not project_result.is_success:
            return project_result

        project = project_result.value

        provider_result = self.embedding_factory.create()

        if not provider_result.is_success:
            return Result.failure(provider_result.error)

        embedding_result = await provider_result.value.embed(
            normalized_query
        )

        if not embedding_result.is_success:
            return Result.failure(embedding_result.error)

        search_result = await self.vector_store.search(
            self.collection_name,
            embedding_result.value,
            limit=limit,
            filters=VectorSearchFilter(project_id=project.project_id),
        )

        if not search_result.is_success:
            return Result.failure(search_result.error)

        return Result.success(search_result.value or [])

    async def _resolve_project(
        self,
        project_id: str,
    ) -> Result[Project]:
        project = await self.project_repository.get_by_project_id(
            project_id
        )

        if project is None:
            return Result.failure(
                ResultError(
                    code=ErrorCode.PROJECT_NOT_FOUND,
                    message=ErrorMessage.PROJECT_NOT_FOUND,
                    type=ErrorType.NOT_FOUND,
                )
            )

        if project.id is None:
            return Result.failure(
                ResultError(
                    code=ErrorCode.INVALID_PROJECT_ID,
                    message=ErrorMessage.PROJECT_ID_MISSING,
                    type=ErrorType.INTERNAL,
                )
            )

        return Result.success(project)

    async def _build_vector_records(
        self,
        chunks: list[DataChunk],
        provider: EmbeddingProvider,
        project_id: str,
    ) -> Result[list[VectorRecord]]:
        records: list[VectorRecord] = []

        for chunk in chunks:
            if chunk.id is None:
                return Result.failure(
                    ResultError(
                        code=ErrorCode.INVALID_CHUNK_ID,
                        message=ErrorMessage.INVALID_CHUNK_ID,
                        type=ErrorType.INTERNAL,
                    )
                )

            embedding_result = await provider.embed(chunk.chunk_text)

            if not embedding_result.is_success:
                return Result.failure(embedding_result.error)

            records.append(
                VectorRecord(
                    vector_id=chunk_vector_id(chunk.id),
                    vector=embedding_result.value,
                    metadata={
                        "project_id": project_id,
                        "asset_id": str(chunk.chunk_asset_id),
                        "chunk_id": str(chunk.id),
                        "chunk_index": chunk.chunk_order,
                        "text": chunk.chunk_text,
                    },
                )
            )

        return Result.success(records)
