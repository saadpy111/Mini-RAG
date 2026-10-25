from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase

from src.models.project import Project


class ProjectRepository:
    def __init__(self, database: AsyncDatabase):
        self.collection = database["projects"]

    async def create(self, project: Project) -> Project:
        document = project.model_dump(
            by_alias=True,
            exclude_none=True,
        )

        result = await self.collection.insert_one(document)

        document["_id"] = result.inserted_id

        return Project.model_validate(document)

    async def get_by_project_id(
        self,
        project_id: str,
    ) -> Project | None:
        document = await self.collection.find_one(
            {"project_id": project_id}
        )

        if document is None:
            return None

        return Project.model_validate(document)

    async def get_by_id(
        self,
        project_id: ObjectId,
    ) -> Project | None:
        document = await self.collection.find_one(
            {"_id": project_id}
        )

        if document is None:
            return None

        return Project.model_validate(document)

    async def delete(self, project_id: ObjectId) -> bool:
        result = await self.collection.delete_one(
            {"_id": project_id}
        )

        return result.deleted_count > 0
