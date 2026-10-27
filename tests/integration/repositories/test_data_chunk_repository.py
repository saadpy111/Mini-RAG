import pytest
from bson import ObjectId

pytestmark = pytest.mark.integration


def build_chunks(make_data_chunk, project_id, asset_id, count, prefix="chunk"):
    return [
        make_data_chunk(
            project_id,
            asset_id,
            text=f"{prefix}-{index}",
            order=index,
            metadata={"source": f"{prefix}.txt", "index": index},
        )
        for index in range(1, count + 1)
    ]


def test_create_chunk_persists_fields_and_assigns_id(
    run_async,
    chunk_repository,
    make_data_chunk,
):
    project_id = ObjectId()
    asset_id = ObjectId()
    chunk = make_data_chunk(
        project_id,
        asset_id,
        text="chunk body",
        order=1,
        metadata={"source": "file.txt", "page": 3},
    )

    async def scenario():
        created = await chunk_repository.create_chunk(chunk)

        assert created.id is not None
        assert created.chunk_text == "chunk body"

        fetched = await chunk_repository.get_chunk_by_id(created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.chunk_text == "chunk body"
        assert fetched.chunk_order == 1
        assert fetched.chunk_project_id == project_id
        assert fetched.chunk_asset_id == asset_id
        assert fetched.chunk_metadata == {"source": "file.txt", "page": 3}

    run_async(scenario())


def test_get_chunk_by_id_returns_none_for_missing_chunk(
    run_async,
    chunk_repository,
):
    assert run_async(chunk_repository.get_chunk_by_id(ObjectId())) is None


def test_insert_many_chunks_batches_and_returns_count(
    run_async,
    chunk_repository,
    make_data_chunk,
):
    project_id = ObjectId()
    asset_id = ObjectId()
    chunks = build_chunks(make_data_chunk, project_id, asset_id, 5)

    async def scenario():
        inserted = await chunk_repository.insert_many_chunks(
            chunks=chunks,
            batch_size=2,
        )

        stored = await chunk_repository.get_chunks_by_project_id(
            project_id=project_id,
            page_size=100,
            page_num=1,
        )

        assert inserted == 5
        assert len(stored) == 5
        assert {chunk.chunk_text for chunk in stored} == {
            chunk.chunk_text for chunk in chunks
        }
        assert [chunk.chunk_order for chunk in sorted(
            stored, key=lambda item: item.chunk_order
        )] == [1, 2, 3, 4, 5]
        assert all(chunk.id is not None for chunk in stored)

    run_async(scenario())


def test_insert_many_chunks_accepts_empty_list(
    run_async,
    chunk_repository,
):
    assert (
        run_async(chunk_repository.insert_many_chunks([], batch_size=2)) == 0
    )


@pytest.mark.parametrize("batch_size", [0, -1])
def test_insert_many_chunks_rejects_invalid_batch_size(
    run_async,
    chunk_repository,
    make_data_chunk,
    batch_size,
):
    chunks = [make_data_chunk(ObjectId(), ObjectId())]

    with pytest.raises(ValueError, match="batch_size"):
        run_async(
            chunk_repository.insert_many_chunks(
                chunks=chunks,
                batch_size=batch_size,
            )
        )


def test_get_chunk_ids_by_project_and_asset_is_scoped(
    run_async,
    chunk_repository,
    make_data_chunk,
):
    project_id = ObjectId()
    asset_id = ObjectId()
    other_asset_id = ObjectId()
    other_project_id = ObjectId()

    matching = build_chunks(
        make_data_chunk,
        project_id,
        asset_id,
        2,
        prefix="matching",
    )
    other_asset = build_chunks(
        make_data_chunk,
        project_id,
        other_asset_id,
        1,
        prefix="other-asset",
    )
    other_project = build_chunks(
        make_data_chunk,
        other_project_id,
        asset_id,
        1,
        prefix="other-project",
    )

    async def scenario():
        await chunk_repository.insert_many_chunks(matching)
        await chunk_repository.insert_many_chunks(other_asset)
        await chunk_repository.insert_many_chunks(other_project)

        ids = await chunk_repository.get_chunk_ids_by_project_and_asset(
            project_id=project_id,
            asset_id=asset_id,
        )
        stored = await chunk_repository.get_chunks_by_project_id(
            project_id=project_id,
            page_size=100,
            page_num=1,
        )
        expected_ids = {
            chunk.id
            for chunk in stored
            if chunk.chunk_asset_id == asset_id
            and chunk.chunk_project_id == project_id
        }

        assert len(ids) == 2
        assert set(ids) == expected_ids
        assert len(set(ids)) == len(ids)

    run_async(scenario())


def test_delete_by_ids_only_deletes_captured_ids(
    run_async,
    chunk_repository,
    make_data_chunk,
):
    project_id = ObjectId()
    asset_id = ObjectId()
    other_asset_id = ObjectId()
    other_project_id = ObjectId()

    async def scenario():
        await chunk_repository.insert_many_chunks(
            build_chunks(make_data_chunk, project_id, asset_id, 2, prefix="a")
        )
        await chunk_repository.insert_many_chunks(
            build_chunks(
                make_data_chunk,
                project_id,
                other_asset_id,
                2,
                prefix="b",
            )
        )
        await chunk_repository.insert_many_chunks(
            build_chunks(
                make_data_chunk,
                other_project_id,
                asset_id,
                1,
                prefix="c",
            )
        )

        captured = await chunk_repository.get_chunk_ids_by_project_and_asset(
            project_id=project_id,
            asset_id=asset_id,
        )
        deleted = await chunk_repository.delete_by_ids(captured)

        remaining_project_chunks = (
            await chunk_repository.get_chunks_by_project_id(
                project_id=project_id,
                page_size=100,
                page_num=1,
            )
        )
        remaining_other_project = (
            await chunk_repository.get_chunks_by_project_id(
                project_id=other_project_id,
                page_size=100,
                page_num=1,
            )
        )

        assert deleted == 2
        assert len(captured) == 2
        assert len(remaining_project_chunks) == 2
        assert all(
            chunk.chunk_asset_id == other_asset_id
            for chunk in remaining_project_chunks
        )
        assert len(remaining_other_project) == 1
        assert remaining_other_project[0].chunk_asset_id == asset_id

        for chunk_id in captured:
            assert await chunk_repository.get_chunk_by_id(chunk_id) is None

    run_async(scenario())


def test_delete_by_ids_returns_zero_for_empty_list(
    run_async,
    chunk_repository,
):
    assert run_async(chunk_repository.delete_by_ids([])) == 0


def test_get_chunks_by_project_id_paginates(
    run_async,
    chunk_repository,
    make_data_chunk,
):
    project_id = ObjectId()
    asset_id = ObjectId()
    other_project_id = ObjectId()

    async def scenario():
        await chunk_repository.insert_many_chunks(
            build_chunks(make_data_chunk, project_id, asset_id, 5)
        )
        await chunk_repository.insert_many_chunks(
            build_chunks(
                make_data_chunk,
                other_project_id,
                asset_id,
                2,
                prefix="other",
            )
        )

        page_one = await chunk_repository.get_chunks_by_project_id(
            project_id=project_id,
            page_size=2,
            page_num=1,
        )
        page_two = await chunk_repository.get_chunks_by_project_id(
            project_id=project_id,
            page_size=2,
            page_num=2,
        )
        page_three = await chunk_repository.get_chunks_by_project_id(
            project_id=project_id,
            page_size=2,
            page_num=3,
        )
        page_four = await chunk_repository.get_chunks_by_project_id(
            project_id=project_id,
            page_size=2,
            page_num=4,
        )

        assert len(page_one) == 2
        assert len(page_two) == 2
        assert len(page_three) == 1
        assert page_four == []
        assert all(
            chunk.chunk_project_id == project_id
            for chunk in page_one + page_two + page_three
        )

        all_ids = [
            chunk.id for chunk in page_one + page_two + page_three
        ]
        assert len(all_ids) == 5
        assert len(set(all_ids)) == 5

    run_async(scenario())


@pytest.mark.parametrize(
    ("page_size", "page_num"),
    [(0, 1), (-1, 1), (1, 0), (1, -1)],
)
def test_get_chunks_by_project_id_rejects_invalid_pagination(
    run_async,
    chunk_repository,
    page_size,
    page_num,
):
    with pytest.raises(ValueError):
        run_async(
            chunk_repository.get_chunks_by_project_id(
                project_id=ObjectId(),
                page_size=page_size,
                page_num=page_num,
            )
        )


def test_delete_by_project_id_only_deletes_target_project(
    run_async,
    chunk_repository,
    make_data_chunk,
):
    project_id = ObjectId()
    other_project_id = ObjectId()
    asset_id = ObjectId()

    async def scenario():
        await chunk_repository.insert_many_chunks(
            build_chunks(make_data_chunk, project_id, asset_id, 3)
        )
        await chunk_repository.insert_many_chunks(
            build_chunks(
                make_data_chunk,
                other_project_id,
                asset_id,
                2,
                prefix="other",
            )
        )

        deleted = await chunk_repository.delete_by_project_id(project_id)

        assert deleted == 3
        assert (
            await chunk_repository.get_chunks_by_project_id(
                project_id=project_id,
                page_size=100,
                page_num=1,
            )
            == []
        )
        remaining = await chunk_repository.get_chunks_by_project_id(
            project_id=other_project_id,
            page_size=100,
            page_num=1,
        )
        assert len(remaining) == 2
        assert all(
            chunk.chunk_project_id == other_project_id
            for chunk in remaining
        )

    run_async(scenario())


def test_delete_by_project_id_returns_zero_for_empty_project(
    run_async,
    chunk_repository,
):
    assert (
        run_async(chunk_repository.delete_by_project_id(ObjectId())) == 0
    )
