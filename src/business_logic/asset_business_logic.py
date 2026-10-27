
from bson import ObjectId

from src.models.asset import Asset
from src.repositories.asset_repository import AssetRepository
from src.repositories.project_repository import ProjectRepository
from src.helpers.result_pattern import Result, ResultError, ErrorType


class AssetBusinessLogic:
    def __init__(
        self,
        asset_repository: AssetRepository,
        project_repository: ProjectRepository,
    ):
        self.asset_repository = asset_repository
        self.project_repository = project_repository

    async def create_asset(
        self,
        asset: Asset,
    ) -> Result[Asset]:
        project = await self.project_repository.get_by_id(
            asset.asset_project_id
        )

        if project is None:
            return Result.failure(
                ResultError(
                    code="project_not_found",
                    message="Project not found.",
                    type=ErrorType.NOT_FOUND,
                )
            )

        if not asset.asset_name.strip():
            return Result.failure(
                ResultError(
                    code="invalid_asset_name",
                    message="Asset name cannot be empty.",
                    type=ErrorType.VALIDATION,
                )
            )

        created_asset = await self.asset_repository.create(asset)

        return Result.success(created_asset)

    async def get_asset_by_id(
        self,
        asset_id: ObjectId,
        project_id: ObjectId,
    ) -> Result[Asset]:
        project = await self.project_repository.get_by_id(project_id)

        if project is None:
            return Result.failure(
                ResultError(
                    code="project_not_found",
                    message="Project not found.",
                    type=ErrorType.NOT_FOUND,
                )
            )

        asset = await self.asset_repository.get_by_id_and_project(
            asset_id=asset_id,
            project_id=project_id,
        )

        if asset is None:
            return Result.failure(
                ResultError(
                    code="asset_not_found",
                    message="Asset not found.",
                    type=ErrorType.NOT_FOUND,
                )
            )

        return Result.success(asset)

    async def get_asset_by_file_id(
        self,
        project_id: ObjectId,
        file_id: str,
    ) -> Result[Asset]:
        project = await self.project_repository.get_by_id(project_id)

        if project is None:
            return Result.failure(
                ResultError(
                    code="project_not_found",
                    message="Project not found.",
                    type=ErrorType.NOT_FOUND,
                )
            )

        asset = await self.asset_repository.get_by_project_and_file_id(
            project_id=project_id,
            file_id=file_id,
        )

        if asset is None:
            return Result.failure(
                ResultError(
                    code="asset_not_found",
                    message="Asset not found for the specified file.",
                    type=ErrorType.NOT_FOUND,
                )
            )

        return Result.success(asset)

    async def get_all_assets_by_project_id(
        self,
        project_id: ObjectId,
    ) -> Result[list[Asset]]:
        project = await self.project_repository.get_by_id(project_id)

        if project is None:
            return Result.failure(
                ResultError(
                    code="project_not_found",
                    message="Project not found.",
                    type=ErrorType.NOT_FOUND,
                )
            )

        assets = await self.asset_repository.get_all_by_project_id(
            project_id
        )

        return Result.success(assets)

    async def get_assets_by_project_id(
        self,
        project_id: ObjectId,
        page_size: int = 20,
        page_num: int = 1,
    ) -> Result[list[Asset]]:
        if page_size <= 0 or page_num <= 0:
            return Result.failure(
                ResultError(
                    code="invalid_pagination",
                    message="Page size and page number must be greater than zero.",
                    type=ErrorType.VALIDATION,
                )
            )

        if page_size > 100:
            return Result.failure(
                ResultError(
                    code="page_size_too_large",
                    message="Page size cannot exceed 100.",
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

        skip = (page_num - 1) * page_size

        assets = await self.asset_repository.get_by_project_id(
            project_id=project_id,
            skip=skip,
            limit=page_size,
        )

        return Result.success(assets)

    async def count_assets_by_project_id(
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

        count = await self.asset_repository.count_by_project_id(
            project_id
        )

        return Result.success(count)

    async def delete_asset(
        self,
        asset_id: ObjectId,
        project_id: ObjectId,
    ) -> Result[bool]:
        project = await self.project_repository.get_by_id(project_id)

        if project is None:
            return Result.failure(
                ResultError(
                    code="project_not_found",
                    message="Project not found.",
                    type=ErrorType.NOT_FOUND,
                )
            )

        deleted = await self.asset_repository.delete(
            asset_id=asset_id,
            project_id=project_id,
        )

        if not deleted:
            return Result.failure(
                ResultError(
                    code="asset_not_found",
                    message="Asset not found.",
                    type=ErrorType.NOT_FOUND,
                )
            )

        return Result.success(True)
