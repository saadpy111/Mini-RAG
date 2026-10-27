import asyncio
from unittest.mock import AsyncMock

import pytest
from pymongo.errors import PyMongoError

from src.business_logic.asset_business_logic import AssetBusinessLogic
from src.helpers.result_pattern import ErrorType, Result, ResultError
from src.repositories.asset_repository import AssetRepository
from src.repositories.project_repository import ProjectRepository


@pytest.fixture
def asset_repository():
    return AsyncMock(spec=AssetRepository)


@pytest.fixture
def project_repository():
    return AsyncMock(spec=ProjectRepository)


@pytest.fixture
def logic(asset_repository, project_repository):
    return AssetBusinessLogic(
        asset_repository=asset_repository,
        project_repository=project_repository,
    )


def test_create_asset_succeeds_for_existing_project(
    logic,
    asset_repository,
    project_repository,
    project,
    asset,
):
    project_repository.get_by_id.return_value = project
    asset_repository.create.return_value = asset

    result = asyncio.run(logic.create_asset(asset))

    assert result.is_success is True
    assert result.value is asset
    project_repository.get_by_id.assert_awaited_once_with(asset.asset_project_id)
    asset_repository.create.assert_awaited_once_with(asset)


def test_create_asset_rejects_missing_project(
    logic,
    asset_repository,
    project_repository,
    asset,
):
    project_repository.get_by_id.return_value = None

    result = asyncio.run(logic.create_asset(asset))

    assert result.is_success is False
    assert result.error.code == "project_not_found"
    assert result.error.type is ErrorType.NOT_FOUND
    asset_repository.create.assert_not_awaited()


def test_create_asset_rejects_blank_asset_name(
    logic,
    asset_repository,
    project_repository,
    project,
    make_asset,
):
    project_repository.get_by_id.return_value = project
    asset = make_asset(project.id, asset_name="   ")

    result = asyncio.run(logic.create_asset(asset))

    assert result.is_success is False
    assert result.error.code == "invalid_asset_name"
    assert result.error.type is ErrorType.VALIDATION
    asset_repository.create.assert_not_awaited()


def test_create_asset_propagates_repository_exception(
    logic,
    asset_repository,
    project_repository,
    project,
    asset,
):
    project_repository.get_by_id.return_value = project
    asset_repository.create.side_effect = PyMongoError("write failed")

    with pytest.raises(PyMongoError):
        asyncio.run(logic.create_asset(asset))


def test_get_asset_by_file_id_returns_project_scoped_asset(
    logic,
    asset_repository,
    project_repository,
    project,
    asset,
):
    project_repository.get_by_id.return_value = project
    asset_repository.get_by_project_and_file_id.return_value = asset

    result = asyncio.run(
        logic.get_asset_by_file_id(project.id, file_id="file-1")
    )

    assert result.is_success is True
    assert result.value is asset
    asset_repository.get_by_project_and_file_id.assert_awaited_once_with(
        project_id=project.id,
        file_id="file-1",
    )


def test_get_asset_by_file_id_returns_project_not_found(
    logic,
    asset_repository,
    project_repository,
    project,
):
    project_repository.get_by_id.return_value = None

    result = asyncio.run(
        logic.get_asset_by_file_id(project.id, file_id="file-1")
    )

    assert result.is_success is False
    assert result.error.code == "project_not_found"
    assert result.error.type is ErrorType.NOT_FOUND
    asset_repository.get_by_project_and_file_id.assert_not_awaited()


def test_get_asset_by_file_id_returns_asset_not_found_for_other_project(
    logic,
    asset_repository,
    project_repository,
    project,
):
    project_repository.get_by_id.return_value = project
    asset_repository.get_by_project_and_file_id.return_value = None

    result = asyncio.run(
        logic.get_asset_by_file_id(project.id, file_id="file-from-other-project")
    )

    assert result.is_success is False
    assert result.error.code == "asset_not_found"
    assert result.error.message == "Asset not found for the specified file."
    assert result.error.type is ErrorType.NOT_FOUND


def test_get_asset_by_id_returns_asset(
    logic,
    asset_repository,
    project_repository,
    project,
    asset,
):
    project_repository.get_by_id.return_value = project
    asset_repository.get_by_id_and_project.return_value = asset

    result = asyncio.run(logic.get_asset_by_id(asset.id, project.id))

    assert result.is_success is True
    assert result.value is asset
    asset_repository.get_by_id_and_project.assert_awaited_once_with(
        asset_id=asset.id,
        project_id=project.id,
    )


def test_get_asset_by_id_returns_not_found(
    logic,
    asset_repository,
    project_repository,
    project,
    asset,
):
    project_repository.get_by_id.return_value = project
    asset_repository.get_by_id_and_project.return_value = None

    result = asyncio.run(logic.get_asset_by_id(asset.id, project.id))

    assert result.is_success is False
    assert result.error.code == "asset_not_found"
    assert result.error.type is ErrorType.NOT_FOUND


def test_get_all_assets_by_project_id_returns_assets(
    logic,
    asset_repository,
    project_repository,
    project,
    asset,
):
    project_repository.get_by_id.return_value = project
    asset_repository.get_all_by_project_id.return_value = [asset]

    result = asyncio.run(logic.get_all_assets_by_project_id(project.id))

    assert result.is_success is True
    assert result.value == [asset]
    asset_repository.get_all_by_project_id.assert_awaited_once_with(project.id)


def test_get_all_assets_by_project_id_accepts_empty_list(
    logic,
    asset_repository,
    project_repository,
    project,
):
    project_repository.get_by_id.return_value = project
    asset_repository.get_all_by_project_id.return_value = []

    result = asyncio.run(logic.get_all_assets_by_project_id(project.id))

    assert result.is_success is True
    assert result.value == []


def test_get_all_assets_by_project_id_rejects_missing_project(
    logic,
    asset_repository,
    project_repository,
    project,
):
    project_repository.get_by_id.return_value = None

    result = asyncio.run(logic.get_all_assets_by_project_id(project.id))

    assert result.is_success is False
    assert result.error.code == "project_not_found"
    asset_repository.get_all_by_project_id.assert_not_awaited()


def test_paginated_assets_use_expected_skip_and_limit(
    logic,
    asset_repository,
    project_repository,
    project,
    asset,
):
    project_repository.get_by_id.return_value = project
    asset_repository.get_by_project_id.return_value = [asset]

    result = asyncio.run(
        logic.get_assets_by_project_id(
            project.id,
            page_size=10,
            page_num=2,
        )
    )

    assert result.is_success is True
    asset_repository.get_by_project_id.assert_awaited_once_with(
        project_id=project.id,
        skip=10,
        limit=10,
    )


@pytest.mark.parametrize(
    ("page_size", "page_num", "expected_code"),
    [
        (0, 1, "invalid_pagination"),
        (10, 0, "invalid_pagination"),
        (101, 1, "page_size_too_large"),
    ],
)
def test_paginated_assets_reject_invalid_options(
    logic,
    project_repository,
    project,
    page_size,
    page_num,
    expected_code,
):
    result = asyncio.run(
        logic.get_assets_by_project_id(
            project.id,
            page_size=page_size,
            page_num=page_num,
        )
    )

    assert result.is_success is False
    assert result.error.code == expected_code
    assert result.error.type is ErrorType.VALIDATION
    project_repository.get_by_id.assert_not_awaited()


def test_count_assets_by_project_id_returns_count(
    logic,
    asset_repository,
    project_repository,
    project,
):
    project_repository.get_by_id.return_value = project
    asset_repository.count_by_project_id.return_value = 3

    result = asyncio.run(logic.count_assets_by_project_id(project.id))

    assert result.is_success is True
    assert result.value == 3


def test_delete_asset_returns_not_found_when_repository_deletes_nothing(
    logic,
    asset_repository,
    project_repository,
    project,
    asset,
):
    project_repository.get_by_id.return_value = project
    asset_repository.delete.return_value = False

    result = asyncio.run(logic.delete_asset(asset.id, project.id))

    assert result.is_success is False
    assert result.error.code == "asset_not_found"
    assert result.error.type is ErrorType.NOT_FOUND
