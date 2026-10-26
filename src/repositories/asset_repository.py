
from bson import ObjectId
from pymongo import ASCENDING, DESCENDING
from src.models.asset import Asset
from pymongo.asynchronous.database import AsyncDatabase


class AssetRepository:
    def __init__(self, database: AsyncDatabase):
        self._collection = database["assets"]

    async def create(self, asset: Asset) -> Asset:
        asset_data = asset.model_dump(
            by_alias=True,
            exclude={"id"},
        )

        result = await self._collection.insert_one(asset_data)

        asset.id = result.inserted_id
        return asset

    async def get_by_id(self, asset_id: ObjectId) -> Asset | None:
        document = await self._collection.find_one(
            {"_id": asset_id}
        )

        if document is None:
            return None

        return Asset.model_validate(document)

    async def get_by_id_and_project(
        self,
        asset_id: ObjectId,
        project_id: ObjectId,
    ) -> Asset | None:
        document = await self._collection.find_one(
            {
                "_id": asset_id,
                "asset_project_id": project_id,
            }
        )

        if document is None:
            return None

        return Asset.model_validate(document)

    async def get_by_project_id(
        self,
        project_id: ObjectId,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Asset]:
        cursor = (
            self._collection
            .find({"asset_project_id": project_id})
            .sort("asset_pushed_at", DESCENDING)
            .skip(skip)
            .limit(limit)
        )

        documents = await cursor.to_list(length=limit)

        return [
            Asset.model_validate(document)
            for document in documents
        ]

    async def count_by_project_id(
        self,
        project_id: ObjectId,
    ) -> int:
        return await self._collection.count_documents(
            {"asset_project_id": project_id}
        )

    async def delete(
        self,
        asset_id: ObjectId,
        project_id: ObjectId,
    ) -> bool:
        result = await self._collection.delete_one(
            {
                "_id": asset_id,
                "asset_project_id": project_id,
            }
        )

        return result.deleted_count == 1
