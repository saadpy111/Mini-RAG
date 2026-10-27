from datetime import datetime, timedelta, timezone

from bson import ObjectId

import pytest

pytestmark = pytest.mark.integration


def timestamp(day):
    return datetime(2024, 1, day, tzinfo=timezone.utc)


def test_create_persists_asset_and_assigns_id(
    run_async,
    asset_repository,
    make_asset,
):
    project_id = ObjectId()
    asset = make_asset(
        project_id,
        file_id="file-1",
        asset_name="stored.txt",
        asset_size=12,
        asset_config={
            "file_id": "file-1",
            "original_filename": "notes.txt",
        },
    )

    async def scenario():
        created = await asset_repository.create(asset)

        assert created.id is not None
        assert created.id == asset.id

        fetched = await asset_repository.get_by_id(asset.id)
        assert fetched is not None
        assert fetched.id == asset.id
        assert fetched.asset_project_id == project_id
        assert fetched.asset_name == "stored.txt"
        assert fetched.asset_type == ".txt"
        assert fetched.asset_size == 12
        assert fetched.asset_config == {
            "file_id": "file-1",
            "original_filename": "notes.txt",
        }

    run_async(scenario())


def test_get_by_id_returns_none_for_missing_asset(
    run_async,
    asset_repository,
):
    assert run_async(asset_repository.get_by_id(ObjectId())) is None


def test_get_by_id_and_project_is_scoped_by_project(
    run_async,
    asset_repository,
    make_asset,
):
    project_id = ObjectId()
    other_project_id = ObjectId()
    asset = make_asset(project_id)
    other_asset = make_asset(other_project_id)

    async def scenario():
        await asset_repository.create(asset)
        await asset_repository.create(other_asset)

        found = await asset_repository.get_by_id_and_project(
            asset_id=asset.id,
            project_id=project_id,
        )
        wrong_project = await asset_repository.get_by_id_and_project(
            asset_id=asset.id,
            project_id=other_project_id,
        )

        assert found is not None
        assert found.id == asset.id
        assert wrong_project is None

    run_async(scenario())


def test_get_by_project_and_file_id_is_scoped_by_project(
    run_async,
    asset_repository,
    make_asset,
):
    project_id = ObjectId()
    other_project_id = ObjectId()
    matching = make_asset(project_id, file_id="shared-file")
    other_project_match = make_asset(other_project_id, file_id="shared-file")
    different_file = make_asset(project_id, file_id="other-file")

    async def scenario():
        await asset_repository.create(matching)
        await asset_repository.create(other_project_match)
        await asset_repository.create(different_file)

        found = await asset_repository.get_by_project_and_file_id(
            project_id=project_id,
            file_id="shared-file",
        )
        missing = await asset_repository.get_by_project_and_file_id(
            project_id=project_id,
            file_id="missing-file",
        )

        assert found is not None
        assert found.id == matching.id
        assert found.asset_project_id == project_id
        assert missing is None

    run_async(scenario())


def test_get_by_project_id_paginates_and_sorts_newest_first(
    run_async,
    asset_repository,
    make_asset,
):
    project_id = ObjectId()
    assets = []
    for index in range(3):
        asset = make_asset(project_id, file_id=f"file-{index}")
        assets.append(
            asset.model_copy(
                update={"asset_pushed_at": timestamp(index + 1)}
            )
        )
    other_project = make_asset(ObjectId(), file_id="other")

    async def scenario():
        for asset in assets:
            await asset_repository.create(asset)
        await asset_repository.create(other_project)

        first_page = await asset_repository.get_by_project_id(
            project_id=project_id,
            skip=0,
            limit=2,
        )
        second_page = await asset_repository.get_by_project_id(
            project_id=project_id,
            skip=2,
            limit=2,
        )

        assert [asset.id for asset in first_page] == [
            assets[2].id,
            assets[1].id,
        ]
        assert [asset.id for asset in second_page] == [assets[0].id]
        assert all(asset.asset_project_id == project_id for asset in first_page)

    run_async(scenario())


def test_get_all_by_project_id_returns_only_project_assets(
    run_async,
    asset_repository,
    make_asset,
):
    project_id = ObjectId()
    first = make_asset(project_id, file_id="file-1").model_copy(
        update={"asset_pushed_at": timestamp(1)}
    )
    second = make_asset(project_id, file_id="file-2").model_copy(
        update={"asset_pushed_at": timestamp(2)}
    )
    other = make_asset(ObjectId(), file_id="file-3")

    async def scenario():
        await asset_repository.create(first)
        await asset_repository.create(second)
        await asset_repository.create(other)

        assets = await asset_repository.get_all_by_project_id(project_id)

        assert [asset.id for asset in assets] == [second.id, first.id]
        assert all(asset.asset_project_id == project_id for asset in assets)

    run_async(scenario())


def test_count_by_project_id_counts_only_project_assets(
    run_async,
    asset_repository,
    make_asset,
):
    project_id = ObjectId()

    async def scenario():
        await asset_repository.create(make_asset(project_id, file_id="a"))
        await asset_repository.create(make_asset(project_id, file_id="b"))
        await asset_repository.create(make_asset(ObjectId(), file_id="c"))

        count = await asset_repository.count_by_project_id(project_id)

        assert count == 2

    run_async(scenario())


def test_delete_is_scoped_by_asset_and_project(
    run_async,
    asset_repository,
    make_asset,
):
    project_id = ObjectId()
    asset = make_asset(project_id)

    async def scenario():
        await asset_repository.create(asset)

        wrong_project = await asset_repository.delete(
            asset_id=asset.id,
            project_id=ObjectId(),
        )
        assert wrong_project is False
        assert await asset_repository.get_by_id(asset.id) is not None

        deleted = await asset_repository.delete(
            asset_id=asset.id,
            project_id=project_id,
        )
        assert deleted is True
        assert await asset_repository.get_by_id(asset.id) is None

    run_async(scenario())


def test_creating_many_assets_for_same_project_keeps_all(
    run_async,
    asset_repository,
    make_asset,
    mongo_test_database,
):
    project_id = ObjectId()
    base = timestamp(1)

    async def scenario():
        for index in range(5):
            asset = make_asset(project_id, file_id=f"file-{index}")
            asset = asset.model_copy(
                update={
                    "asset_pushed_at": base + timedelta(milliseconds=index)
                }
            )
            await asset_repository.create(asset)

        count = await asset_repository.count_by_project_id(project_id)
        documents = await mongo_test_database["assets"].count_documents(
            {"asset_project_id": project_id}
        )

        assert count == 5
        assert documents == 5

    run_async(scenario())
