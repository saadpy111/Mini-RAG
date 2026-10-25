
from pymongo import ASCENDING
from pymongo.asynchronous.database import AsyncDatabase


async def create_project_indexes(database: AsyncDatabase) -> None:
    projects = database["projects"]

  
    await projects.create_index(
        [("project_id", ASCENDING)],
        unique=True,
        name="uq_projects_project_id",
    )


async def create_data_chunk_indexes(database: AsyncDatabase) -> None:
    data_chunks = database["data_chunks"]

   
    await data_chunks.create_index(
        [
            ("chunk_project_id", ASCENDING)
        ],
        name="ix_chunks_project_id",
    )


async def create_indexes(database: AsyncDatabase) -> None:
    await create_project_indexes(database)
    await create_data_chunk_indexes(database)
