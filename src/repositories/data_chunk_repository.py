
from bson import ObjectId
from pymongo import InsertOne
from pymongo.asynchronous.database import AsyncDatabase

from src.models.data_chunk import DataChunk


class DataChunkRepository:
    def __init__(self, database: AsyncDatabase):
        self.collection = database["data_chunks"]

    async def create_chunk(self, chunk: DataChunk) -> DataChunk:
        document = chunk.model_dump(
            by_alias=True,
            exclude_none=True,
        )

        result = await self.collection.insert_one(document)
        document["_id"] = result.inserted_id

        return DataChunk.model_validate(document)

    async def insert_many_chunks(
        self,
        chunks: list[DataChunk],
        batch_size: int = 100,
    ) -> int:
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero")

        if not chunks:
            return 0

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]

            documents = [
                chunk.model_dump(
                    by_alias=True,
                    exclude_none=True,
                )
                for chunk in batch
            ]

            await self.collection.insert_many(documents)

        return len(chunks)

    async def get_chunk_by_id(
        self,
        chunk_id: ObjectId,
    ) -> DataChunk | None:
        document = await self.collection.find_one(
            {"_id": chunk_id}
        )

        if document is None:
            return None

        return DataChunk.model_validate(document)

    async def get_chunk_ids_by_project_and_asset(
        self,
        project_id: ObjectId,
        asset_id: ObjectId,
    ) -> list[ObjectId]:
        cursor = self.collection.find(
            {
                "chunk_project_id": project_id,
                "chunk_asset_id": asset_id,
            },
            {"_id": 1},
        )

        documents = await cursor.to_list(length=None)

        return [document["_id"] for document in documents]

    async def delete_by_ids(
        self,
        chunk_ids: list[ObjectId],
    ) -> int:
        if not chunk_ids:
            return 0

        result = await self.collection.delete_many(
            {"_id": {"$in": chunk_ids}}
        )

        return result.deleted_count

    async def get_chunks_by_project_id(
        self,
        project_id: ObjectId,
        page_size: int,
        page_num: int,
    ) -> list[DataChunk]:
        if page_size <= 0:
            raise ValueError("page_size must be greater than zero")

        if page_num <= 0:
            raise ValueError("page_num must be greater than zero")

        filter_query = {"chunk_project_id": project_id}
        skip_count = (page_num - 1) * page_size

        cursor = (
            self.collection
            .find(filter_query)
            .skip(skip_count)
            .limit(page_size)
        )

        documents = await cursor.to_list(length=page_size)

        return [
            DataChunk.model_validate(document)
            for document in documents
        ]

    async def delete_by_project_id(
        self,
        project_id: ObjectId,
    ) -> int:
        result = await self.collection.delete_many(
            {"chunk_project_id": project_id}
        )

        return result.deleted_count
