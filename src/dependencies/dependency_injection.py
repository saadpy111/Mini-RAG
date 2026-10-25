
from typing import Annotated

from fastapi import Depends
from pymongo.asynchronous.database import AsyncDatabase

from src.db.dependencies import get_database
from src.repositories.data_chunk_repository import DataChunkRepository
from src.repositories.project_repository import ProjectRepository
from src.business_logic.chunk_business_logic import ChunkBusinessLogic
from src.business_logic.project_business_logic import ProjectBusinessLogic


def get_project_business_logic(
    database: Annotated[
        AsyncDatabase,
        Depends(get_database),
    ],
) -> ProjectBusinessLogic:
    repository = ProjectRepository(database)
    return ProjectBusinessLogic(repository)


def get_chunk_business_logic(
    database: Annotated[
        AsyncDatabase,
        Depends(get_database),
    ],
) -> ChunkBusinessLogic:
    chunk_repository = DataChunkRepository(database)
    project_repository = ProjectRepository(database)

    return ChunkBusinessLogic(
        chunk_repository=chunk_repository,
        project_repository=project_repository,
    )
