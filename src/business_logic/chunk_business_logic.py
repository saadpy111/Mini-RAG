
from bson import ObjectId

from src.models.data_chunk import DataChunk
from src.repositories.data_chunk_repository import DataChunkRepository
from src.repositories.project_repository import ProjectRepository
from src.helpers.result_pattern import Result, ResultError, ErrorType


class ChunkBusinessLogic:
    def __init__(
        self,
        chunk_repository: DataChunkRepository,
        project_repository: ProjectRepository,
    ):
        self.chunk_repository = chunk_repository
        self.project_repository = project_repository

    async def create_chunk(
        self,
        chunk: DataChunk,
    ) -> Result[DataChunk]:
        project = await self.project_repository.get_by_id(
            chunk.chunk_project_id
        )

        if project is None:
            return Result.failure(
                ResultError(
                    code="project_not_found",
                    message="Project not found.",
                    type=ErrorType.NOT_FOUND,
                )
            )

        created_chunk = await self.chunk_repository.create_chunk(chunk)

        return Result.success(created_chunk)

    async def insert_many_chunks(
        self,
        chunks: list[DataChunk],
        batch_size: int = 100,
    ) -> Result[int]:
        if not chunks:
            return Result.failure(
                ResultError(
                    code="empty_chunks",
                    message="Chunks list cannot be empty.",
                    type=ErrorType.VALIDATION,
                )
            )

        if batch_size <= 0:
            return Result.failure(
                ResultError(
                    code="invalid_batch_size",
                    message="Batch size must be greater than zero.",
                    type=ErrorType.VALIDATION,
                )
            )

        project_ids = {chunk.chunk_project_id for chunk in chunks}

        if len(project_ids) != 1:
            return Result.failure(
                ResultError(
                    code="project_id_mismatch",
                    message="All chunks must belong to the same project.",
                    type=ErrorType.VALIDATION,
                )
            )

        project_id = next(iter(project_ids))

        project = await self.project_repository.get_by_id(project_id)

        if project is None:
            return Result.failure(
                ResultError(
                    code="project_not_found",
                    message="Project not found.",
                    type=ErrorType.NOT_FOUND,
                )
            )

        inserted_count = await self.chunk_repository.insert_many_chunks(
            chunks=chunks,
            batch_size=batch_size,
        )

        return Result.success(inserted_count)

    async def get_chunk_by_id(
        self,
        chunk_id: ObjectId,
    ) -> Result[DataChunk]:
        chunk = await self.chunk_repository.get_chunk_by_id(chunk_id)

        if chunk is None:
            return Result.failure(
                ResultError(
                    code="chunk_not_found",
                    message="Chunk not found.",
                    type=ErrorType.NOT_FOUND,
                )
            )

        return Result.success(chunk)

    async def get_chunks_by_project_id(
        self,
        project_id: ObjectId,
        page_size: int = 100,
        page_num: int = 1,
    ) -> Result[list[DataChunk]]:
        if page_size <= 0 or page_num <= 0:
            return Result.failure(
                ResultError(
                    code="invalid_pagination",
                    message="Page size and page number must be greater than zero.",
                    type=ErrorType.VALIDATION,
                )
            )

        project = await self.project_repository.get_by_id(project_id)

        if project is None:
            return Result.failure(
                ResultError(
                    code="project_not_found",
                    message="Project not found.",
                    type=ErrorType.NOT_FOUND,
                )
            )

        chunks = await self.chunk_repository.get_chunks_by_project_id(
            project_id=project_id,
            page_size=page_size,
            page_num=page_num,
        )

        return Result.success(chunks)

    async def delete_by_project_id(
        self,
        project_id: ObjectId,
    ) -> Result[int]:
        project = await self.project_repository.get_by_id(project_id)

        if project is None:
            return Result.failure(
                ResultError(
                    code="project_not_found",
                    message="Project not found.",
                    type=ErrorType.NOT_FOUND,
                )
            )

        deleted_count = await self.chunk_repository.delete_by_project_id(
            project_id
        )

        return Result.success(deleted_count)
