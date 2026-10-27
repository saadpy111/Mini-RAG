
from bson import ObjectId

from src.models.asset import Asset
from src.repositories.asset_repository import AssetRepository
from src.repositories.project_repository import ProjectRepository
from src.constants import ErrorCode, ErrorMessage
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
                    code=ErrorCode.PROJECT_NOT_FOUND,
                    message=ErrorMessage.PROJECT_NOT_FOUND,
                    type=ErrorType.NOT_FOUND,
                )
            )

        if not asset.asset_name.strip():
            return Result.failure(
                ResultError(
                    code=ErrorCode.INVALID_ASSET_NAME,
                    message=ErrorMessage.INVALID_ASSET_NAME,
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
                    code=ErrorCode.PROJECT_NOT_FOUND,
                    message=ErrorMessage.PROJECT_NOT_FOUND,
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
                    code=ErrorCode.ASSET_NOT_FOUND,
                    message=ErrorMessage.ASSET_NOT_FOUND,
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
                    code=ErrorCode.PROJECT_NOT_FOUND,
                    message=ErrorMessage.PROJECT_NOT_FOUND,
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
                    code=ErrorCode.ASSET_NOT_FOUND,
                    message=ErrorMessage.ASSET_NOT_FOUND_FOR_FILE,
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
                    code=ErrorCode.PROJECT_NOT_FOUND,
                    message=ErrorMessage.PROJECT_NOT_FOUND,
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
                    code=ErrorCode.INVALID_PAGINATION,
                    message=ErrorMessage.INVALID_PAGINATION,
                    type=ErrorType.VALIDATION,
                )
            )

        if page_size > 100:
            return Result.failure(
                ResultError(
                    code=ErrorCode.PAGE_SIZE_TOO_LARGE,
                    message=ErrorMessage.PAGE_SIZE_TOO_LARGE,
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
                    code=ErrorCode.PROJECT_NOT_FOUND,
                    message=ErrorMessage.PROJECT_NOT_FOUND,
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
                    code=ErrorCode.PROJECT_NOT_FOUND,
                    message=ErrorMessage.PROJECT_NOT_FOUND,
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
                    code=ErrorCode.ASSET_NOT_FOUND,
                    message=ErrorMessage.ASSET_NOT_FOUND,
                    type=ErrorType.NOT_FOUND,
                )
            )

        return Result.success(True)
