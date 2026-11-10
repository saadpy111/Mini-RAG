import pytest
from bson import ObjectId

from src.models.project import Project

pytestmark = pytest.mark.integration


def test_create_and_get_by_project_id(run_async, project_repository):
    project = Project(project_id="project-1")

    async def scenario():
        created = await project_repository.create(project)

        assert created.id is not None
        assert created.project_id == "project-1"

        fetched = await project_repository.get_by_project_id("project-1")
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.project_id == "project-1"

    run_async(scenario())


def test_get_by_project_id_returns_none_for_unknown_project(
    run_async,
    project_repository,
):
    assert (
        run_async(project_repository.get_by_project_id("missing-project"))
        is None
    )


def test_get_by_id_returns_none_for_unknown_object_id(
    run_async,
    project_repository,
):
    assert run_async(project_repository.get_by_id(ObjectId())) is None
