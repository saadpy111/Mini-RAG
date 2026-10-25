
from src.models.project import Project
from src.repositories.project_repository import ProjectRepository
from src.helpers.result_pattern import ErrorType, Result, ResultError


class ProjectBusinessLogic:
    def __init__(self, project_repository: ProjectRepository):
        self.project_repository = project_repository

    async def create_project(self, project: Project) -> Result[Project]:
        existing_project = await self.project_repository.get_by_project_id(
            project.project_id
        )

        if existing_project is not None:
            return Result.failure(
                ResultError(
                    code="project_already_exists",
                    message="A project with this ID already exists.",
                    type=ErrorType.CONFLICT,
                )
            )

        created_project = await self.project_repository.create(project)

        return Result.success(created_project)

    async def get_project(
        self,
        project_id: str,
    ) -> Result[Project]:
        project = await self.project_repository.get_by_project_id(
            project_id
        )

        if project is None:
            return Result.failure(
                ResultError(
                    code="project_not_found",
                    message="Project was not found.",
                    type=ErrorType.NOT_FOUND,
                )
            )

        return Result.success(project)
