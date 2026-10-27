
from bson import ObjectId
from langchain_core.documents import Document
from pymongo.errors import PyMongoError

from src.models.data_chunk import DataChunk
from src.repositories.data_chunk_repository import DataChunkRepository
from src.repositories.project_repository import ProjectRepository
from src.constants import ErrorCode, ErrorMessage, MessageTemplate
from src.helpers.result_pattern import Result, ResultError, ErrorType


def build_data_chunks(
    documents: list[Document],
    project_id: ObjectId,
    asset_id: ObjectId,
) -> list[DataChunk]:
    return [
        DataChunk(
            chunk_text=document.page_content,
            chunk_metadata=document.metadata,
            chunk_order=index,
            chunk_project_id=project_id,
            chunk_asset_id=asset_id,
        )
        for index, document in enumerate(documents, start=1)
    ]


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
                    code=ErrorCode.PROJECT_NOT_FOUND,
                    message=ErrorMessage.PROJECT_NOT_FOUND,
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
                    code=ErrorCode.EMPTY_CHUNKS,
                    message=ErrorMessage.EMPTY_CHUNKS,
                    type=ErrorType.VALIDATION,
                )
            )

        if batch_size <= 0:
            return Result.failure(
                ResultError(
                    code=ErrorCode.INVALID_BATCH_SIZE,
                    message=ErrorMessage.INVALID_BATCH_SIZE,
                    type=ErrorType.VALIDATION,
                )
            )

        project_ids = {chunk.chunk_project_id for chunk in chunks}

        if len(project_ids) != 1:
            return Result.failure(
                ResultError(
                    code=ErrorCode.PROJECT_ID_MISMATCH,
                    message=ErrorMessage.PROJECT_ID_MISMATCH,
                    type=ErrorType.VALIDATION,
                )
            )

        project_id = next(iter(project_ids))

        asset_ids = {chunk.chunk_asset_id for chunk in chunks}

        if len(asset_ids) != 1:
            return Result.failure(
                ResultError(
                    code=ErrorCode.ASSET_ID_MISMATCH,
                    message=ErrorMessage.ASSET_ID_MISMATCH,
                    type=ErrorType.VALIDATION,
                )
            )

        project = await self.project_repository.get_by_id(project_id)

        if project is None:
            return Result.failure(
                ResultError(
                    code=ErrorCode.PROJECT_NOT_FOUND,
                    message=ErrorMessage.PROJECT_NOT_FOUND,
                    type=ErrorType.NOT_FOUND,
                )
            )

        try:
            inserted_count = await self.chunk_repository.insert_many_chunks(
                chunks=chunks,
                batch_size=batch_size,
            )
        except PyMongoError:
            return Result.failure(
                ResultError(
                    code=ErrorCode.CHUNK_PERSISTENCE_FAILED,
                    message=ErrorMessage.CHUNK_PERSISTENCE_FAILED,
                    type=ErrorType.INTERNAL,
                )
            )

        return Result.success(inserted_count)

    async def replace_chunks_for_asset(
        self,
        project_id: ObjectId,
        asset_id: ObjectId,
        chunks: list[DataChunk],
    ) -> Result[int]:
        if not chunks:
            return Result.failure(
                ResultError(
                    code=ErrorCode.EMPTY_CHUNKS,
                    message=ErrorMessage.EMPTY_CHUNKS,
                    type=ErrorType.VALIDATION,
                )
            )

        if any(
            chunk.chunk_project_id != project_id
            or chunk.chunk_asset_id != asset_id
            for chunk in chunks
        ):
            return Result.failure(
                ResultError(
                    code=ErrorCode.CHUNK_SCOPE_MISMATCH,
                    message=ErrorMessage.CHUNK_SCOPE_MISMATCH,
                    type=ErrorType.VALIDATION,
                )
            )

        try:
            previous_chunk_ids = (
                await self.chunk_repository.get_chunk_ids_by_project_and_asset(
                    project_id=project_id,
                    asset_id=asset_id,
                )
            )
        except PyMongoError:
            return Result.failure(
                ResultError(
                    code=ErrorCode.CHUNK_LOOKUP_FAILED,
                    message=ErrorMessage.CHUNK_LOOKUP_FAILED,
                    type=ErrorType.INTERNAL,
                )
            )

        insert_result = await self.insert_many_chunks(chunks)

        if not insert_result.is_success:
            return insert_result

        inserted_count = insert_result.value

        if not previous_chunk_ids:
            return Result.success(inserted_count)

        try:
            deleted_count = await self.chunk_repository.delete_by_ids(
                previous_chunk_ids
            )
        except PyMongoError:
            return Result.failure(
                ResultError(
                    code=ErrorCode.CHUNK_CLEANUP_FAILED,
                    message=MessageTemplate.CHUNK_CLEANUP_FAILED.format(
                        inserted_count=inserted_count,
                    ),
                    type=ErrorType.INTERNAL,
                )
            )

        if deleted_count != len(previous_chunk_ids):
            return Result.failure(
                ResultError(
                    code=ErrorCode.CHUNK_CLEANUP_FAILED,
                    message=MessageTemplate.CHUNK_CLEANUP_PARTIAL.format(
                        inserted_count=inserted_count,
                        deleted_count=deleted_count,
                        expected_count=len(previous_chunk_ids),
                    ),
                    type=ErrorType.INTERNAL,
                )
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
                    code=ErrorCode.CHUNK_NOT_FOUND,
                    message=ErrorMessage.CHUNK_NOT_FOUND,
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
                    code=ErrorCode.INVALID_PAGINATION,
                    message=ErrorMessage.INVALID_PAGINATION,
                    type=ErrorType.VALIDATION,
                )
            )

        project = await self.project_repository.get_by_id(project_id)

        if project is None:
            return Result.failure(
                ResultError(
                    code=ErrorCode.PROJECT_NOT_FOUND,
                    message=ErrorMessage.PROJECT_NOT_FOUND,
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
                    code=ErrorCode.PROJECT_NOT_FOUND,
                    message=ErrorMessage.PROJECT_NOT_FOUND,
                    type=ErrorType.NOT_FOUND,
                )
            )

        deleted_count = await self.chunk_repository.delete_by_project_id(
            project_id
        )

        return Result.success(deleted_count)
